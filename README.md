# SenseVoice FastAPI WebSocket 实时语音识别服务

基于 SenseVoice 模型的实时语音识别服务，使用 FastAPI + WebSocket 构建现代化的语音转文字应用。

## 🚀 功能特性

- **实时语音识别**: 基于 SenseVoice 的高精度识别
- **流式处理**: WebSocket 实时音频流处理
- **VAD 语音检测**: 智能语音活动检测
- **多语言支持**: 支持中文、英文、日文、韩文、粤语
- **现代 Web 界面**: 响应式设计，实时音频可视化
- **双重识别机制**: 实时识别 + 段落结束识别
- **自动重连**: 网络断线自动重连
- **音频质量监控**: 实时音量检测和质量提示

## 📋 系统要求

- Python 3.8+
- 现代浏览器 (Chrome 80+, Firefox 75+, Safari 13+)
- 麦克风设备

## 🛠️ 安装和配置

### 1. 克隆项目
```bash
git clone <项目地址>
cd sense_voice_standalone
```

### 2. 创建虚拟环境
```bash
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# 或
.venv\Scripts\activate     # Windows
```

### 3. 安装依赖
```bash
uv pip install -r requirements.txt
```

### 4. 模型文件配置
确保 `models/` 目录包含以下文件：
```
models/
├── model.int8.onnx      # SenseVoice 模型
├── tokens.txt           # 词汇表
└── silero_vad.onnx      # VAD 模型
```

## 🚀 启动服务

### 快速启动
```bash
./start_server.sh
```

### 开发模式
```bash
./start_dev.sh
```

### 手动启动
```bash
source .venv/bin/activate
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

## 🌐 访问地址

- **Web 界面**: http://localhost:8000
- **配置页面**: http://localhost:8000/config (VAD参数调整)
- **调试页面**: http://localhost:8000/debug (连接测试)
- **WebSocket**: ws://localhost:8000/ws/recognize
- **健康检查**: http://localhost:8000/health
- **API 文档**: http://localhost:8000/docs

## 📱 使用说明

1. **打开浏览器**: 访问 http://localhost:8000
2. **允许麦克风权限**: 浏览器会请求麦克风访问权限
3. **开始录音**: 点击"开始录音"按钮
4. **实时识别**: 对着麦克风说话，可以看到实时识别结果
5. **查看结果**: 识别结果会实时显示在界面上

## 🎛️ 配置选项

### 语言设置
- 自动检测
- 中文
- 英文
- 日文
- 韩文
- 粤语

### 逆文本标准化 (ITN)
- 启用/禁用数字、日期、时间等的格式转换

## 🏗️ 项目结构

```
sense_voice_standalone/
├── main.py                 # FastAPI 主应用
├── requirements.txt        # Python 依赖
├── README.md              # 项目说明
├── start_server.sh        # 生产启动脚本
├── start_dev.sh           # 开发启动脚本
├── FastAPI_WebSocket_开发文档.md  # 详细开发文档
├── static/                # 前端静态文件
│   ├── index.html        # 主页面
│   ├── app.js            # 前端逻辑
│   └── style.css         # 样式文件
└── models/               # 模型文件目录
    ├── model.int8.onnx
    ├── tokens.txt
    └── silero_vad.onnx
```

## 🔌 API 接口

### WebSocket 连接
```
ws://localhost:8000/ws/recognize
```

### 消息格式

#### 客户端发送
```json
{
  "type": "config",
  "language": "auto",
  "use_itn": true
}
```

#### 服务端返回
```json
{
  "type": "partial",
  "text": "实时识别结果",
  "timestamp": "2024-01-01T12:00:00.000Z",
  "confidence": 0.95
}

{
  "type": "final",
  "text": "最终识别结果",
  "timestamp": "2024-01-01T12:00:01.000Z",
  "confidence": 0.98,
  "segment_id": 1
}
```

## 🎯 核心算法

### 双重触发识别机制
1. **实时识别**: 每 0.2 秒触发一次，提供即时反馈
2. **段落结束识别**: VAD 检测到语音结束时触发，提供更准确的结果

### VAD 语音活动检测
- 静音阈值: 0.5
- 最小静音时长: 100ms
- 最小语音时长: 250ms
- 最大语音时长: 8秒

## 🔧 故障排除

### 常见问题

1. **无法连接到服务器**
   - 检查服务器是否正常启动
   - 确认端口 8000 未被占用
   - 检查防火墙设置

2. **麦克风权限被拒绝**
   - 在浏览器设置中允许麦克风权限
   - 确保系统已连接麦克风设备

3. **识别准确率低**
   - 确保环境安静，减少背景噪音
   - 调整麦克风距离和音量
   - 选择正确的语言设置

4. **模型加载失败**
   - 检查模型文件是否完整
   - 确认模型文件路径正确
   - 检查文件权限

### 日志查看
```bash
# 查看服务器日志
tail -f /var/log/sensevoice.log

# 查看错误日志
grep ERROR /var/log/sensevoice.log
```

## 🚀 性能优化

### 服务器端
- 使用 GPU 加速 (如果可用)
- 调整线程池大小
- 启用模型缓存

### 客户端
- 使用现代浏览器
- 确保网络连接稳定
- 关闭不必要的标签页

## 🤝 贡献指南

1. Fork 项目
2. 创建功能分支
3. 提交更改
4. 推送到分支
5. 创建 Pull Request

## 📄 许可证

本项目基于 MIT 许可证开源。

## 🙏 致谢

- [Sherpa-ONNX](https://github.com/k2-fsa/sherpa-onnx) - 语音识别框架
- [FastAPI](https://fastapi.tiangolo.com/) - Web 框架
- [SenseVoice](https://github.com/FunAudioLLM/SenseVoice) - 语音识别模型

## 📞 支持

如有问题或建议，请提交 Issue 或联系开发团队。