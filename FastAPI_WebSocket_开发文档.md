# SenseVoice FastAPI WebSocket 后端开发文档

## 项目概述

基于 `sense_voice_standalone/run.py` 的流式语音识别能力，将其改造为 FastAPI WebSocket 后端服务，提供实时语音转文字功能。

## 系统架构

```
┌─────────────────┐    WebSocket     ┌─────────────────┐
│   前端客户端     │ ◄──────────────► │  FastAPI 后端   │
│  (录音/播放)     │                  │                 │
└─────────────────┘                  │  ┌─────────────┐│
                                     │  │  VAD 检测   ││
                                     │  └─────────────┘│
                                     │  ┌─────────────┐│
                                     │  │SenseVoice   ││
                                     │  │  模型推理    ││
                                     │  └─────────────┘│
                                     └─────────────────┘
```

## 1. 后端接口文档

### 1.1 WebSocket 连接端点

**端点**: `ws://localhost:8000/ws/recognize`

**连接方式**:
```javascript
const ws = new WebSocket('ws://localhost:8000/ws/recognize');
```

### 1.2 接口参数

#### 客户端发送的消息格式

**音频数据消息**:
```
类型: Binary (二进制数据)
格式: float32 数组
采样率: 16000 Hz
通道数: 1 (单声道)
数据块大小: 建议 1600 样本 (100ms)
```

**控制消息**:
```json
{
  "type": "config",
  "language": "auto",  // "auto", "zh", "en", "ja", "ko", "yue"
  "use_itn": true      // 是否启用逆文本标准化
}
```

**结束消息**:
```json
{
  "type": "done"
}
```

#### 服务端返回的消息格式

**识别结果消息**:
```json
{
  "type": "partial",     // 部分结果 (实时)
  "text": "你好",
  "timestamp": "2024-01-01T12:00:00.000Z",
  "confidence": 0.95
}
```

```json
{
  "type": "final",       // 最终结果 (段落结束)
  "text": "你好世界",
  "timestamp": "2024-01-01T12:00:01.000Z",
  "confidence": 0.98,
  "segment_id": 1
}
```

**状态消息**:
```json
{
  "type": "status",
  "message": "Connected successfully",
  "model_loaded": true
}
```

**错误消息**:
```json
{
  "type": "error",
  "message": "Model loading failed",
  "code": 500
}
```

### 1.3 后端核心逻辑

#### 1.3.1 模型初始化
```python
# 全局单例模式，启动时加载一次
class SenseVoiceService:
    def __init__(self):
        self.recognizer = sherpa_onnx.OfflineRecognizer.from_sense_voice(
            model="models/model.int8.onnx",
            tokens="models/tokens.txt",
            use_itn=True,
            num_threads=2
        )

        self.vad_config = sherpa_onnx.VadModelConfig()
        self.vad_config.silero_vad.model = "models/silero_vad.onnx"
        self.vad_config.silero_vad.threshold = 0.5
        self.vad_config.silero_vad.min_silence_duration = 0.1
        self.vad_config.silero_vad.min_speech_duration = 0.25
        self.vad_config.silero_vad.max_speech_duration = 8
        self.vad_config.sample_rate = 16000
```

#### 1.3.2 WebSocket 连接处理流程
```
1. 客户端连接 → 发送状态消息确认连接
2. 接收配置消息 → 设置识别参数
3. 开始音频流处理循环
   ├─ 接收音频块
   ├─ 添加到缓冲区
   ├─ VAD 检测语音活动
   ├─ 实时识别 (每 0.2s 触发)
   └─ 段落结束识别 (VAD 触发)
4. 接收结束消息 → 清理资源 → 断开连接
```

#### 1.3.3 双重触发识别机制

**实时识别触发** (每 0.2s):
- 条件: `started and time.time() - started_time > 0.2`
- 返回: 部分识别结果，持续更新
- 优点: 提供实时反馈，用户体验好

**段落结束识别触发** (VAD 检测到语音结束):
- 条件: `vad.empty() == False`
- 返回: 最终识别结果，准确率更高
- 优点: 完整语音段落，识别准确

#### 1.3.4 VAD 音频分段处理
```python
# 缓冲区管理
buffer = []           # 音频数据缓冲区
offset = 0           # 处理偏移量
window_size = 512    # VAD 窗口大小

# VAD 处理循环
while offset + window_size < len(buffer):
    vad.accept_waveform(buffer[offset : offset + window_size])

    # 检测到语音开始
    if not started and vad.is_speech_detected():
        started = True
        started_time = time.time()

    offset += window_size
```

### 1.4 并发和资源管理

#### 1.4.1 连接管理
- **最大并发连接数**: 100 (可配置)
- **连接超时**: 300 秒
- **心跳检测**: 每 30 秒发送 ping 消息

#### 1.4.2 资源优化策略
```python
# 线程池处理识别任务
recognition_executor = ThreadPoolExecutor(max_workers=4)

# 识别任务队列
recognition_queue = asyncio.Queue(maxsize=1000)

# 内存管理
max_buffer_size = 16000 * 10  # 最大缓冲 10 秒音频
```

## 2. 前端开发文档

### 2.1 技术栈要求

- **浏览器**: Chrome 80+, Firefox 75+, Safari 13+
- **Web Audio API**: 用于音频采集和处理
- **WebSocket API**: 用于实时通信

### 2.2 音频采集配置

#### 2.2.1 getUserMedia 参数
```javascript
const audioConstraints = {
    audio: {
        sampleRate: 16000,
        channelCount: 1,
        echoCancellation: true,
        noiseSuppression: true,
        autoGainControl: true
    }
};

const stream = await navigator.mediaDevices.getUserMedia(audioConstraints);
```

#### 2.2.2 音频处理设置
```javascript
// AudioContext 配置
const audioContext = new AudioContext({
    sampleRate: 16000,
    latencyHint: 'interactive'
});

// 创建 ScriptProcessor 进行音频处理
const source = audioContext.createMediaStreamSource(stream);
const processor = audioContext.createScriptProcessor(4096, 1, 1);

processor.onaudioprocess = (event) => {
    const inputBuffer = event.inputBuffer;
    const inputData = inputBuffer.getChannelData(0);

    // 转换为 float32 格式
    const float32Array = new Float32Array(inputData);

    // 发送到后端
    if (websocket.readyState === WebSocket.OPEN) {
        websocket.send(float32Array.buffer);
    }
};
```

### 2.3 WebSocket 客户端实现

#### 2.3.1 连接建立
```javascript
class SpeechRecognitionClient {
    constructor(url) {
        this.url = url;
        this.websocket = null;
        this.onPartialResult = null;
        this.onFinalResult = null;
        this.onError = null;
        this.onStatus = null;
    }

    async connect() {
        try {
            this.websocket = new WebSocket(this.url);

            this.websocket.onopen = () => {
                // 发送配置消息
                this.sendConfig({
                    language: 'auto',
                    use_itn: true
                });
            };

            this.websocket.onmessage = (event) => {
                const message = JSON.parse(event.data);
                this.handleMessage(message);
            };

            this.websocket.onerror = (error) => {
                this.handleError(error);
            };

        } catch (error) {
            this.handleError(error);
        }
    }
}
```

#### 2.3.2 消息处理
```javascript
handleMessage(message) {
    switch (message.type) {
        case 'partial':
            if (this.onPartialResult) {
                this.onPartialResult(message.text, message.confidence);
            }
            break;

        case 'final':
            if (this.onFinalResult) {
                this.onFinalResult(message.text, message.confidence, message.segment_id);
            }
            break;

        case 'status':
            if (this.onStatus) {
                this.onStatus(message.message);
            }
            break;

        case 'error':
            this.handleError(message);
            break;
    }
}
```

### 2.4 UI 组件设计

#### 2.4.1 录音控制组件
```javascript
class RecordingControl {
    constructor() {
        this.isRecording = false;
        this.audioContext = null;
        this.mediaStream = null;
        this.recognitionClient = null;
    }

    async startRecording() {
        try {
            // 请求麦克风权限
            this.mediaStream = await navigator.mediaDevices.getUserMedia({
                audio: {
                    sampleRate: 16000,
                    channelCount: 1
                }
            });

            // 初始化音频处理
            this.setupAudioProcessing();

            // 连接 WebSocket
            await this.recognitionClient.connect();

            this.isRecording = true;
            this.updateUI('recording');

        } catch (error) {
            this.handleError(error);
        }
    }

    stopRecording() {
        if (this.mediaStream) {
            this.mediaStream.getTracks().forEach(track => track.stop());
        }

        if (this.recognitionClient) {
            this.recognitionClient.sendDone();
            this.recognitionClient.disconnect();
        }

        this.isRecording = false;
        this.updateUI('stopped');
    }
}
```

#### 2.4.2 结果显示组件
```javascript
class ResultDisplay {
    constructor() {
        this.partialResultElement = document.getElementById('partial-result');
        this.finalResultsElement = document.getElementById('final-results');
        this.currentSegment = 1;
    }

    updatePartialResult(text, confidence) {
        this.partialResultElement.textContent = text;
        this.partialResultElement.style.opacity = confidence;
    }

    addFinalResult(text, confidence, segmentId) {
        const resultElement = document.createElement('div');
        resultElement.className = 'final-result';
        resultElement.innerHTML = `
            <span class="segment-id">[${segmentId}]</span>
            <span class="text">${text}</span>
            <span class="confidence">${(confidence * 100).toFixed(1)}%</span>
        `;

        this.finalResultsElement.appendChild(resultElement);
        this.partialResultElement.textContent = '';
    }
}
```

### 2.5 错误处理和重连机制

#### 2.5.1 连接错误处理
```javascript
handleError(error) {
    console.error('WebSocket Error:', error);

    // 用户友好的错误提示
    let errorMessage = '连接出现问题，请检查网络后重试';

    if (error.name === 'NotAllowedError') {
        errorMessage = '请允许使用麦克风权限';
    } else if (error.name === 'NotFoundError') {
        errorMessage = '未找到麦克风设备';
    }

    this.showErrorMessage(errorMessage);

    // 自动重连机制
    if (this.autoReconnect) {
        setTimeout(() => {
            this.connect();
        }, 3000);
    }
}
```

#### 2.5.2 音频质量监控
```javascript
monitorAudioQuality(inputData) {
    // 音量检测
    const volume = Math.sqrt(inputData.reduce((sum, val) => sum + val * val, 0) / inputData.length);

    if (volume < 0.01) {
        this.showWarning('说话声音太小，请靠近麦克风');
    } else if (volume > 0.8) {
        this.showWarning('声音太大，可能影响识别效果');
    }

    // 静音检测
    this.silenceTimer = volume > 0.01 ? 0 : this.silenceTimer + 1;

    if (this.silenceTimer > 100) { // 10秒静音
        this.showWarning('长时间未检测到语音，请检查麦克风');
    }
}
```

## 3. 部署和配置

### 3.1 后端部署

#### 3.1.1 依赖安装
```bash
pip install fastapi uvicorn websockets numpy sounddevice sherpa-onnx
```

#### 3.1.2 启动命令
```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 1
```

#### 3.1.3 模型文件配置
```
models/
├── model.int8.onnx      # SenseVoice 模型文件
├── tokens.txt           # 词汇表文件
└── silero_vad.onnx      # VAD 模型文件
```

### 3.2 前端部署

#### 3.2.1 静态文件服务
```javascript
// FastAPI 静态文件服务
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def read_root():
    return FileResponse('static/index.html')
```

#### 3.2.2 HTTPS 配置 (生产环境)
```javascript
// 生产环境需要 HTTPS 才能访问麦克风
const wsUrl = `wss://${window.location.host}/ws/recognize`;
```

## 4. 性能优化建议

### 4.1 后端优化
- 使用 GPU 加速模型推理
- 实现连接池管理
- 添加识别结果缓存
- 使用负载均衡处理高并发

### 4.2 前端优化
- 实现音频数据压缩传输
- 添加音频预处理降噪
- 优化渲染性能，避免频繁 DOM 操作
- 使用 Web Worker 处理音频数据

### 4.3 网络优化
- 实现音频数据分包传输
- 添加网络状态检测
- 实现断线重连机制
- 优化音频数据包大小

## 5. 测试建议

### 5.1 功能测试
- [ ] 基本连接和通信
- [ ] 音频识别准确性
- [ ] 实时性能测试
- [ ] 多语言支持测试
- [ ] 错误处理测试

### 5.2 性能测试
- [ ] 并发连接测试
- [ ] 长时间稳定性测试
- [ ] 内存使用监控
- [ ] 网络延迟测试

### 5.3 兼容性测试
- [ ] 不同浏览器测试
- [ ] 不同设备测试
- [ ] 网络环境测试
- [ ] 音频设备兼容性测试