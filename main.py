#!/usr/bin/env python3
"""
SenseVoice FastAPI WebSocket 主应用
只包含路由定义，业务逻辑移至 server 模块
"""
import logging
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, WebSocket
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, Response

from server.sensevoice_service import SenseVoiceService
from server.websocket_manager import WebSocketConnectionManager
from server.websocket_handler import WebSocketHandler

# 创建自定义日志过滤器，过滤掉WebSocket二进制和TEXT日志
class WebSocketLogFilter(logging.Filter):
    def filter(self, record):
        # 过滤掉包含特定内容的日志
        if hasattr(record, 'getMessage'):
            message = record.getMessage()
            # 过滤掉二进制数据和WebSocket消息
            if ('BINARY' in message or
                'TEXT' in message or
                message.startswith('>') or
                message.startswith('<')):
                return False
        return True

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# 应用过滤器到根日志记录器
root_logger = logging.getLogger()
for handler in root_logger.handlers:
    handler.addFilter(WebSocketLogFilter())

# 过滤掉所有WebSocket相关的DEBUG日志
loggers_to_silence = [
    "websockets",
    "uvicorn.websocket",
    "uvicorn.access",
    "uvicorn.error",
    "fastapi.websocket",
    "uvicorn.protocols.websockets.websockets_impl"
]

for logger_name in loggers_to_silence:
    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.CRITICAL)  # 只显示严重错误

logger = logging.getLogger(__name__)


# 全局服务实例
sense_voice_service = None
connection_manager = None
websocket_handler = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    global sense_voice_service, connection_manager, websocket_handler

    # 启动时初始化
    logger.info("正在启动 SenseVoice 服务...")
    sense_voice_service = SenseVoiceService()
    connection_manager = WebSocketConnectionManager()
    websocket_handler = WebSocketHandler(sense_voice_service, connection_manager)
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
        return sense_voice_service.get_vad_config()
    return {"error": "Service not initialized"}


@app.websocket("/ws/recognize")
async def websocket_recognize(websocket: WebSocket):
    """WebSocket 语音识别端点"""
    if websocket_handler:
        await websocket_handler.handle_websocket_connection(websocket)


@app.get("/health")
async def health_check():
    """健康检查端点"""
    return {
        "status": "healthy",
        "model_loaded": sense_voice_service is not None,
        "active_connections": connection_manager.get_connection_count() if connection_manager else 0
    }


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8891,
        reload=True,
        log_level="info",
        access_log=False  # 禁用访问日志减少噪音
    )