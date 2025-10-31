#!/bin/bash

# SenseVoice FastAPI 服务启动脚本

echo "🎤 启动 SenseVoice FastAPI WebSocket 服务..."

# 检查虚拟环境
if [ ! -d ".venv" ]; then
    echo "❌ 虚拟环境不存在，请先创建虚拟环境"
    echo "运行: python -m venv .venv"
    exit 1
fi

# 激活虚拟环境
echo "📦 激活虚拟环境..."
source .venv/bin/activate

# 检查模型文件
echo "🔍 检查模型文件..."
required_files=(
    "models/model.int8.onnx"
    "models/tokens.txt"
    "models/silero_vad.onnx"
)

for file in "${required_files[@]}"; do
    if [ ! -f "$file" ]; then
        echo "❌ 缺少模型文件: $file"
        echo "请确保所有模型文件都在 models/ 目录中"
        exit 1
    fi
done

echo "✅ 模型文件检查完成"

# 安装依赖
echo "📥 检查并安装依赖..."
uv pip install -r requirements.txt

# 检查端口是否被占用
PORT=8000
if lsof -Pi :$PORT -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo "⚠️  端口 $PORT 已被占用，尝试终止现有进程..."
    lsof -ti:$PORT | xargs kill -9 2>/dev/null || true
    sleep 2
fi

# 启动服务
echo "🚀 启动服务器..."
echo "📱 服务地址: http://localhost:$PORT"
echo "🔗 WebSocket: ws://localhost:$PORT/ws/recognize"
echo "📊 健康检查: http://localhost:$PORT/health"
echo ""
echo "按 Ctrl+C 停止服务"
echo "=========================="

# 使用 uvicorn 启动服务
uvicorn main:app \
    --host 0.0.0.0 \
    --port $PORT \
    --reload \
    --log-level info \
    --access-log