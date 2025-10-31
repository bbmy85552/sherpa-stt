#!/usr/bin/env python3
"""
运行SenseVoice语音识别的独立脚本
"""
import os
import subprocess
import sys

def main():
    # 检查模型文件是否存在
    model_dir = "models"
    required_files = [
        "model.int8.onnx",
        "tokens.txt",
        "silero_vad.onnx"
    ]

    for file in required_files:
        file_path = os.path.join(model_dir, file)
        if not os.path.exists(file_path):
            print(f" 错误: 缺少必需文件 {file_path}")
            return 1

    print("所有模型文件检查完成")
    print("启动SenseVoice语音识别...")

    # 运行脚本
    cmd = [
        "python3", "simulate-streaming-sense-voice-microphone.py",
        "--silero-vad-model=models/silero_vad.onnx",
        "--sense-voice=models/model.int8.onnx",
        "--tokens=models/tokens.txt"
    ]

    try:
        subprocess.run(cmd, check=True)
    except KeyboardInterrupt:
        print("\n程序已停止")
    except subprocess.CalledProcessError as e:
        print(f"运行错误: {e}")
        return 1

    return 0

if __name__ == "__main__":
    sys.exit(main())