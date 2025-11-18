#!/usr/bin/env python3
"""
SenseVoice 服务类
管理模型加载和识别逻辑
"""
import logging
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
import sherpa_onnx

# 配置日志
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
                language="yue",  # 设置为普通话中文，支持粤语请使用 "yue"
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

    def get_vad_config(self):
        """获取当前VAD配置"""
        return {
            "threshold": self.vad_config.silero_vad.threshold,
            "min_silence_duration": self.vad_config.silero_vad.min_silence_duration,
            "min_speech_duration": self.vad_config.silero_vad.min_speech_duration,
            "max_speech_duration": self.vad_config.silero_vad.max_speech_duration,
            "realtime_interval": 0.5  # 实时识别间隔
        }