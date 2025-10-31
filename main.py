#!/usr/bin/env python3
"""
SenseVoice FastAPI WebSocket 后端服务
基于 run.py 的流式语音识别能力改造
"""
import asyncio
import json
import logging
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
import sherpa_onnx
import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, Response

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class SenseVoiceService:
    """SenseVoice 服务类，管理模型加载和识别逻辑"""

    def __init__(self):
        self.model_dir = Path("models")
        self.sample_rate = 16000
        self._initialize_models()

    def _initialize_models(self):
        """初始化识别器和VAD模型"""
        try:
            # 检查模型文件
            model_files = {
                "sense_voice": "model.int8.onnx",
                "tokens": "tokens.txt",
                "silero_vad": "silero_vad.onnx"
            }

            for file_name in model_files.values():
                file_path = self.model_dir / file_name
                if not file_path.exists():
                    raise FileNotFoundError(f"模型文件不存在: {file_path}")

            # 初始化 SenseVoice 识别器
            logger.info("正在加载 SenseVoice 模型...")
            self.recognizer = sherpa_onnx.OfflineRecognizer.from_sense_voice(
                model=str(self.model_dir / "model.int8.onnx"),
                tokens=str(self.model_dir / "tokens.txt"),
                use_itn=True,
                num_threads=2,
                debug=False
            )
            logger.info("SenseVoice 模型加载成功")

            # 初始化 VAD
            logger.info("正在加载 VAD 模型...")
            self.vad_config = sherpa_onnx.VadModelConfig()
            self.vad_config.silero_vad.model = str(self.model_dir / "silero_vad.onnx")
            self.vad_config.silero_vad.threshold = 0.4  # 降低灵敏度，减少误触发
            self.vad_config.silero_vad.min_silence_duration = 0.8  # 800ms，增加静音容忍时间
            self.vad_config.silero_vad.min_speech_duration = 0.3  # 300ms，稍微增加最小语音时长
            self.vad_config.silero_vad.max_speech_duration = 15  # 15秒，支持更长语音
            self.vad_config.sample_rate = self.sample_rate

            self.window_size = self.vad_config.silero_vad.window_size
            logger.info("VAD 模型加载成功")

        except Exception as e:
            logger.error(f"模型初始化失败: {e}")
            raise

    def create_vad_instance(self):
        """创建新的VAD实例"""
        return sherpa_onnx.VoiceActivityDetector(
            self.vad_config,
            buffer_size_in_seconds=100
        )


class WebSocketConnectionManager:
    """WebSocket 连接管理器"""

    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.connection_configs: Dict[str, dict] = {}

    async def connect(self, websocket: WebSocket, connection_id: str):
        """接受新连接"""
        await websocket.accept()
        self.active_connections[connection_id] = websocket
        logger.info(f"新连接: {connection_id}, 当前连接数: {len(self.active_connections)}")

    def disconnect(self, connection_id: str):
        """断开连接"""
        if connection_id in self.active_connections:
            del self.active_connections[connection_id]
        if connection_id in self.connection_configs:
            del self.connection_configs[connection_id]
        logger.info(f"连接断开: {connection_id}, 当前连接数: {len(self.active_connections)}")

    async def send_message(self, connection_id: str, message: dict):
        """发送消息到指定连接"""
        if connection_id in self.active_connections:
            websocket = self.active_connections[connection_id]
            try:
                await websocket.send_text(json.dumps(message, ensure_ascii=False))
            except Exception as e:
                logger.error(f"发送消息失败 {connection_id}: {e}")
                self.disconnect(connection_id)


# 全局服务实例
sense_voice_service = None
connection_manager = WebSocketConnectionManager()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    global sense_voice_service

    # 启动时初始化
    logger.info("正在启动 SenseVoice 服务...")
    sense_voice_service = SenseVoiceService()
    logger.info("SenseVoice 服务启动完成")

    yield

    # 关闭时清理
    logger.info("正在关闭 SenseVoice 服务...")


app = FastAPI(
    title="SenseVoice 语音识别服务",
    description="基于 SenseVoice 的实时语音识别 WebSocket 服务",
    version="1.0.0",
    lifespan=lifespan
)

# 静态文件服务
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
async def read_root():
    """主页"""
    return FileResponse('static/index.html')


@app.get("/debug")
async def debug_page():
    """调试页面"""
    return FileResponse('debug.html')


@app.get("/config")
async def config_page():
    """配置页面"""
    return FileResponse('config.html')


@app.get("/favicon.ico")
async def favicon():
    """Favicon"""
    return Response(status_code=204)  # 返回空响应


@app.get("/.well-known/appspecific/com.chrome.devtools.json")
async def devtools():
    """Chrome DevTools"""
    return Response(status_code=404)


@app.get("/api/vad-config")
async def get_vad_config():
    """获取当前VAD配置"""
    if sense_voice_service:
        return {
            "threshold": sense_voice_service.vad_config.silero_vad.threshold,
            "min_silence_duration": sense_voice_service.vad_config.silero_vad.min_silence_duration,
            "min_speech_duration": sense_voice_service.vad_config.silero_vad.min_speech_duration,
            "max_speech_duration": sense_voice_service.vad_config.silero_vad.max_speech_duration,
            "realtime_interval": 0.5  # 实时识别间隔
        }
    return {"error": "Service not initialized"}


@app.websocket("/ws/recognize")
async def websocket_recognize(websocket: WebSocket):
    """WebSocket 语音识别端点"""
    connection_id = f"conn_{id(websocket)}"

    try:
        await connection_manager.connect(websocket, connection_id)

        # 发送连接成功消息
        await connection_manager.send_message(connection_id, {
            "type": "status",
            "message": "Connected successfully",
            "model_loaded": True
        })

        # 等待配置消息
        config_message = await websocket.receive_text()
        config = json.loads(config_message)

        if config.get("type") != "config":
            await connection_manager.send_message(connection_id, {
                "type": "error",
                "message": "Missing configuration message",
                "code": 400
            })
            return

        connection_manager.connection_configs[connection_id] = config
        logger.info(f"连接 {connection_id} 配置: {config}")

        # 创建 VAD 实例
        vad = sense_voice_service.create_vad_instance()

        # 音频处理变量
        buffer = []
        offset = 0
        started = False
        started_time = None
        segment_id = 1

        logger.info(f"开始处理音频流: {connection_id}")

        # 主处理循环
        while True:
            try:
                # 接收音频数据
                data = await websocket.receive_bytes()
                samples = np.frombuffer(data, dtype=np.float32)

                # 添加到缓冲区
                buffer = np.concatenate([buffer, samples])

                # VAD 处理
                while offset + sense_voice_service.window_size < len(buffer):
                    vad.accept_waveform(
                        buffer[offset : offset + sense_voice_service.window_size]
                    )

                    # 检测到语音开始
                    if not started and vad.is_speech_detected():
                        started = True
                        started_time = time.time()
                        logger.info(f"检测到语音开始: {connection_id}")

                    offset += sense_voice_service.window_size

                # 缓冲区大小控制
                if not started and len(buffer) > 10 * sense_voice_service.window_size:
                    offset -= len(buffer) - 10 * sense_voice_service.window_size
                    buffer = buffer[-10 * sense_voice_service.window_size :]

                # 实时识别 (每 0.5s，减少触发频率)
                if started and time.time() - started_time > 0.5:
                    try:
                        stream = sense_voice_service.recognizer.create_stream()
                        stream.accept_waveform(sense_voice_service.sample_rate, buffer)
                        sense_voice_service.recognizer.decode_stream(stream)
                        text = stream.result.text.strip()

                        if text:
                            await connection_manager.send_message(connection_id, {
                                "type": "partial",
                                "text": text,
                                "timestamp": time.time(),
                                "confidence": 0.95  # SenseVoice 暂不支持置信度
                            })

                        started_time = time.time()

                    except Exception as e:
                        logger.error(f"实时识别错误 {connection_id}: {e}")

                # 段落结束识别
                while not vad.empty():
                    try:
                        segment_samples = vad.front.samples
                        stream = sense_voice_service.recognizer.create_stream()
                        stream.accept_waveform(sense_voice_service.sample_rate, segment_samples)

                        vad.pop()
                        sense_voice_service.recognizer.decode_stream(stream)
                        text = stream.result.text.strip()

                        if text:
                            await connection_manager.send_message(connection_id, {
                                "type": "final",
                                "text": text,
                                "timestamp": time.time(),
                                "confidence": 0.98,  # SenseVoice 暂不支持置信度
                                "segment_id": segment_id
                            })
                            segment_id += 1

                        # 重置状态
                        buffer = []
                        offset = 0
                        started = False
                        started_time = None

                    except Exception as e:
                        logger.error(f"段落识别错误 {connection_id}: {e}")

            except WebSocketDisconnect:
                break
            except Exception as e:
                logger.error(f"处理音频数据错误 {connection_id}: {e}")
                await connection_manager.send_message(connection_id, {
                    "type": "error",
                    "message": f"处理音频数据错误: {str(e)}",
                    "code": 500
                })

    except WebSocketDisconnect:
        logger.info(f"WebSocket 连接断开: {connection_id}")
    except Exception as e:
        logger.error(f"WebSocket 连接错误 {connection_id}: {e}")
    finally:
        connection_manager.disconnect(connection_id)


@app.get("/health")
async def health_check():
    """健康检查端点"""
    return {
        "status": "healthy",
        "model_loaded": sense_voice_service is not None,
        "active_connections": len(connection_manager.active_connections)
    }


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )