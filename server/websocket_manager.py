#!/usr/bin/env python3
"""
WebSocket 连接管理器
管理所有WebSocket连接的注册、断开和消息发送
"""
import json
import logging
from typing import Dict

from fastapi import WebSocket

# 配置日志
logger = logging.getLogger(__name__)


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

    def get_connection_count(self) -> int:
        """获取当前活跃连接数"""
        return len(self.active_connections)

    def set_connection_config(self, connection_id: str, config: dict):
        """设置连接配置"""
        self.connection_configs[connection_id] = config

    def get_connection_config(self, connection_id: str) -> dict:
        """获取连接配置"""
        return self.connection_configs.get(connection_id, {})