#!/bin/bash

# SenseVoice 开发模式启动脚本

echo "🛠️  启动 SenseVoice 开发模式..."

# 激活虚拟环境
source .venv/bin/activate

# 设置开发环境变量
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
export ENV=development

# 检查模型文件
if [ ! -f "models/model.int8.onnx" ] || [ ! -f "models/tokens.txt" ] || [ ! -f "models/silero_vad.onnx" ]; then
    echo "❌ 模型文件不完整，请检查 models/ 目录"
    exit 1
fi

echo "🚀 启动开发服务器 (支持热重载)..."
echo "📱 访问地址: http://localhost:8891"
echo ""

# 开发模式启动
uvicorn main:app \
    --host 0.0.0.0 \
    --port 8891 \
    --reload \
    --reload-dir static \
    --reload-dir . \
    --log-level debug \
    --access-log \
    --workers 1