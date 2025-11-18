#!/usr/bin/env python3
"""
WebSocket 处理逻辑
处理音频流识别的具体业务逻辑
"""
import asyncio
import json
import logging
import time
from collections import deque
from typing import Optional

import numpy as np
from fastapi import WebSocket, WebSocketDisconnect

from .sensevoice_service import SenseVoiceService
from .websocket_manager import WebSocketConnectionManager

# 配置日志
logger = logging.getLogger(__name__)


class AudioBuffer:
    """环形音频缓冲区，限制最大时长，避免无限扩容"""

    def __init__(self, sample_rate: int, max_duration: float):
        self.sample_rate = sample_rate
        self.max_samples = max(1, int(sample_rate * max_duration))
        self.chunks = deque()
        self.total_samples = 0

    def append(self, samples: np.ndarray):
        if not isinstance(samples, np.ndarray):
            samples = np.asarray(samples, dtype=np.float32)
        if samples.size == 0:
            return
        self.chunks.append(samples)
        self.total_samples += samples.shape[0]
        self._trim()

    def _trim(self):
        while self.total_samples > self.max_samples and self.chunks:
            removed = self.chunks.popleft()
            self.total_samples -= removed.shape[0]

    def clear(self):
        self.chunks.clear()
        self.total_samples = 0

    def get_recent_samples(self, duration_seconds: Optional[float] = None) -> np.ndarray:
        """获取最近一段音频数据"""
        if self.total_samples == 0:
            return np.array([], dtype=np.float32)

        target_samples = self.max_samples
        if duration_seconds is not None:
            target_samples = min(self.total_samples, int(duration_seconds * self.sample_rate))
        else:
            target_samples = min(self.total_samples, target_samples)

        if target_samples <= 0:
            return np.array([], dtype=np.float32)

        collected = []
        remaining = target_samples
        for chunk in reversed(self.chunks):
            if remaining <= 0:
                break
            if chunk.shape[0] <= remaining:
                collected.append(chunk)
                remaining -= chunk.shape[0]
            else:
                collected.append(chunk[-remaining:])
                remaining = 0

        if not collected:
            return np.array([], dtype=np.float32)

        collected.reverse()
        return np.concatenate(collected).astype(np.float32, copy=False)


class WebSocketHandler:
    """WebSocket 处理器，处理音频识别的具体逻辑"""

    def __init__(self, sense_voice_service: SenseVoiceService, connection_manager: WebSocketConnectionManager):
        self.sense_voice_service = sense_voice_service
        self.connection_manager = connection_manager
        # 可调参数
        self.recv_timeout = 2.0  # 等待音频超时时间
        self.idle_timeout = 10.0  # 没有音频输入的断开时间
        self.ping_interval = 5.0  # 心跳间隔
        self.pong_timeout = 3.0  # 心跳响应超时
        self.idle_sleep = 0.01  # 空闲时的让步时间
        self.partial_interval = 0.5  # 实时识别最小间隔
        self.partial_window_seconds = 2.0  # 实时识别只解码最近音频
        self.buffer_duration_seconds = 6.0  # 最大缓冲时长

    async def handle_websocket_connection(self, websocket: WebSocket):
        """处理WebSocket连接"""
        connection_id = f"conn_{id(websocket)}"

        try:
            await self.connection_manager.connect(websocket, connection_id)

            # 发送连接成功消息
            await self.connection_manager.send_message(connection_id, {
                "type": "status",
                "message": "Connected successfully",
                "model_loaded": True
            })

            # 等待配置消息
            config_message = await websocket.receive_text()
            config = json.loads(config_message)

            if config.get("type") != "config":
                await self.connection_manager.send_message(connection_id, {
                    "type": "error",
                    "message": "Missing configuration message",
                    "code": 400
                })
                return

            self.connection_manager.set_connection_config(connection_id, config)
            logger.info(f"🔗 WebSocket连接建立: {connection_id}")

            vad = self.sense_voice_service.create_vad_instance()
            audio_buffer = AudioBuffer(
                self.sense_voice_service.sample_rate,
                self.buffer_duration_seconds
            )
            leftover = np.array([], dtype=np.float32)
            started = False
            segment_id = 1
            last_partial_time = 0.0
            last_activity = time.monotonic()
            last_audio_activity = last_activity
            last_ping_time = 0.0
            awaiting_pong = False

            logger.info(f"🎤 开始音频流处理: {connection_id}")

            while True:
                now = time.monotonic()
                try:
                    message = await asyncio.wait_for(websocket.receive(), timeout=self.recv_timeout)
                except asyncio.TimeoutError:
                    idle_duration = now - last_audio_activity
                    activity_duration = now - last_activity

                    if idle_duration > self.idle_timeout:
                        await self._notify_timeout(connection_id, "长时间未检测到语音，连接已关闭")
                        await self._safe_close(websocket, code=1001, reason="idle timeout")
                        break

                    if awaiting_pong and now - last_ping_time > self.pong_timeout:
                        await self._notify_timeout(connection_id, "未收到心跳响应，连接已关闭")
                        await self._safe_close(websocket, code=1011, reason="pong timeout")
                        break

                    if (not awaiting_pong) and activity_duration > self.ping_interval:
                        await self.connection_manager.send_message(connection_id, {"type": "ping"})
                        awaiting_pong = True
                        last_ping_time = now

                    await asyncio.sleep(self.idle_sleep)
                    continue
                except WebSocketDisconnect:
                    break
                except Exception as e:
                    logger.error(f"处理音频数据错误 {connection_id}: {e}")
                    await self.connection_manager.send_message(connection_id, {
                        "type": "error",
                        "message": f"处理音频数据错误: {str(e)}",
                        "code": 500
                    })
                    await asyncio.sleep(self.idle_sleep)
                    continue

                message_type = message.get("type")
                if message_type == "websocket.disconnect":
                    break
                if message_type != "websocket.receive":
                    continue

                binary_data = message.get("bytes")
                text_data = message.get("text")

                if binary_data is not None:
                    samples = np.frombuffer(binary_data, dtype=np.float32)
                    if samples.size == 0:
                        continue

                    audio_buffer.append(samples)
                    last_audio_activity = time.monotonic()
                    last_activity = last_audio_activity
                    awaiting_pong = False

                    leftover, started = self._process_vad_frames(
                        vad, samples, leftover, started, connection_id
                    )

                    if started:
                        monotonic_now = time.monotonic()
                        if monotonic_now - last_partial_time >= self.partial_interval:
                            partial_samples = audio_buffer.get_recent_samples(self.partial_window_seconds)
                            if partial_samples.size > 0:
                                await self._realtime_recognition(partial_samples, connection_id)
                                last_partial_time = monotonic_now

                    segment_id, drained = await self._drain_vad_segments(
                        vad, connection_id, segment_id, audio_buffer
                    )
                    if drained:
                        started = False
                        last_partial_time = 0.0
                        leftover = np.array([], dtype=np.float32)

                    continue

                if text_data is not None:
                    last_activity = time.monotonic()
                    msg_type, payload = self._parse_control_message(text_data, connection_id)

                    if msg_type == "pong":
                        awaiting_pong = False
                        continue

                    if msg_type in {"heartbeat", "status"}:
                        continue

                    if msg_type == "config" and payload:
                        # 允许连接期间动态更新设置
                        self.connection_manager.set_connection_config(connection_id, payload)
                        continue

                    if msg_type == "done":
                        segment_id, drained = await self._drain_vad_segments(
                            vad, connection_id, segment_id, audio_buffer
                        )
                        if drained:
                            started = False
                            last_partial_time = 0.0
                            leftover = np.array([], dtype=np.float32)
                        continue

                    if msg_type is not None:
                        logger.info(f"收到控制消息 {connection_id}: {msg_type}")
                    continue

        except WebSocketDisconnect:
            logger.info(f"🔌 WebSocket连接断开: {connection_id}")
        except Exception as e:
            logger.error(f"WebSocket 连接错误 {connection_id}: {e}")
        finally:
            self.connection_manager.disconnect(connection_id)

    def _process_vad_frames(
        self,
        vad,
        samples: np.ndarray,
        leftover: np.ndarray,
        started: bool,
        connection_id: str
    ):
        """仅处理新增音频，避免重复扫描整个缓冲区"""
        if leftover.size > 0:
            working = np.concatenate((leftover, samples))
        else:
            working = samples

        window_size = self.sense_voice_service.window_size
        if working.shape[0] < window_size:
            return working, started

        processed = (working.shape[0] // window_size) * window_size
        for index in range(0, processed, window_size):
            frame = working[index : index + window_size]
            vad.accept_waveform(frame)
            if not started and vad.is_speech_detected():
                started = True
                logger.info(f"🎯 检测到语音开始: {connection_id}")

        remaining = working[processed:]
        return remaining, started

    async def _drain_vad_segments(
        self,
        vad,
        connection_id: str,
        segment_id: int,
        audio_buffer: AudioBuffer
    ):
        """VAD 检测到段落结束时触发最终识别"""
        drained = False
        while not vad.empty():
            drained = True
            await self._final_segment_recognition(vad, connection_id, segment_id)
            segment_id += 1

        if drained:
            audio_buffer.clear()

        return segment_id, drained

    def _parse_control_message(self, text_data: str, connection_id: str):
        try:
            payload = json.loads(text_data)
        except json.JSONDecodeError:
            logger.warning(f"无法解析控制消息 {connection_id}: {text_data}")
            return None, None

        return payload.get("type"), payload

    async def _notify_timeout(self, connection_id: str, message: str):
        await self.connection_manager.send_message(connection_id, {
            "type": "timeout",
            "message": message,
            "timestamp": time.time()
        })

    async def _safe_close(self, websocket: WebSocket, code: int, reason: str):
        try:
            await websocket.close(code=code, reason=reason)
        except Exception:
            pass

    async def _realtime_recognition(self, buffer: np.ndarray, connection_id: str):
        """实时识别处理"""
        try:
            stream = self.sense_voice_service.recognizer.create_stream()
            stream.accept_waveform(self.sense_voice_service.sample_rate, buffer)
            self.sense_voice_service.recognizer.decode_stream(stream)
            text = stream.result.text.strip()

            if text:
                logger.info(f"📝 实时识别结果 {connection_id}: {text}")
                await self.connection_manager.send_message(connection_id, {
                    "type": "partial",
                    "text": text,
                    "timestamp": time.time(),
                    "confidence": 0.95  # SenseVoice 暂不支持置信度
                })

        except Exception as e:
            logger.error(f"实时识别错误 {connection_id}: {e}")

    async def _final_segment_recognition(self, vad, connection_id: str, segment_id: int):
        """段落结束识别处理"""
        try:
            segment_samples = vad.front.samples
            stream = self.sense_voice_service.recognizer.create_stream()
            stream.accept_waveform(self.sense_voice_service.sample_rate, segment_samples)

            vad.pop()
            self.sense_voice_service.recognizer.decode_stream(stream)
            text = stream.result.text.strip()

            if text:
                logger.info(f"✅ 最终识别结果 {connection_id} [段落{segment_id}]: {text}")
                await self.connection_manager.send_message(connection_id, {
                    "type": "final",
                    "text": text,
                    "timestamp": time.time(),
                    "confidence": 0.98,  # SenseVoice 暂不支持置信度
                    "segment_id": segment_id
                })

        except Exception as e:
            logger.error(f"段落识别错误 {connection_id}: {e}")
