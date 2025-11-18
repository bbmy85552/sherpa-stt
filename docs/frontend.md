markdown
SenseVoice 前端功能介绍
🎯 核心功能概览
1. 实时语音识别
功能描述: 用户点击“开始录音”后，实时将麦克风输入的语音转换为文字
当前状态: ✅ 功能完整可用
实现方式: WebSocket + Web Audio API + SenseVoice 模型
用户体验: 说话时可以看到实时识别结果（partial text），语句结束时显示最终结果（final text）
2. 音频可视化
功能描述: 实时显示音频波形的动态可视化效果
当前状态: ✅ 功能完整可用
实现方式: Canvas 绘制，根据音频振幅生成渐变色波形图
用户体验: 说话时能看到蓝色到红色的渐变波形，静音时波形平缓
3. 连接状态监控
功能描述: 显示与后端 WebSocket 连接的状态
当前状态: ✅ 功能完整可用
实现方式: WebSocket 事件监听
用户体验: 显示“已连接”/“未连接”状态，断线时自动重连（最多5次）
4. 音频质量监控
功能描述: 实时检测音频质量并给出提示
当前状态: ✅ 功能完整可用
实现方式: 音量分析和质量评估算法
用户体验: 音量太小提示“靠近麦克风”，音量过大提示“声音太大”

⚠️ 当前假功能（展示用）
1. 语言选择下拉框

html
<select id="languageSelect">
<option value="auto">自动检测</option>
<option value="zh">中文</option>
<option value="en">英文</option>
<option value="ja">日文</option>
<option value="ko">韩文</option>
<option value="yue">粤语</option>
</select>
当前状态: 🚫 假功能 - 仅展示用
用户行为: 可以选择不同语言选项
实际效果: 没有作用，始终使用 SenseVoice 的自动语言检测
前端发送: 会发送 {"language": "zh"} 等配置到后端
后端处理: 接收配置但忽略不处理
如何改为真功能:

修改 server/sensevoice_service.py：

python
def create_recognizer(self, language="auto", use_itn=True):
# SenseVoice 支持的语言参数映射
language_mapping = {
"auto": None, # 自动检测
"zh": "chinese",
"en": "english",
"ja": "japanese",
"ko": "korean",
"yue": "chinese" # 粤语使用中文模型
}

lang_param = language_mapping.get(language)

self.recognizer = sherpa_onnx.OfflineRecognizer.from_sense_voice(
model=str(self.model_dir / "model.int8.onnx"),
tokens=str(self.model_dir / "tokens.txt"),
language=lang_param, # 动态语言参数
use_itn=use_itn,
num_threads=2,
debug=False
)

2. 逆文本标准化复选框

html
<input type="checkbox" id="useItn" checked>
启用逆文本标准化
当前状态: 🚫 假功能 - 仅展示用
用户行为: 可以勾选/取消勾选
实际效果: 没有作用，始终启用 ITN
前端发送: 会发送 {"use_itn": true/false} 到后端
后端处理: 硬编码 use_itn=True，忽略用户选择
如何改为真功能:

修改 server/websocket_handler.py：

python
async def handle_websocket_connection(self, websocket: WebSocket):
# ... 配置接收后
config = self.connection_manager.get_connection_config(connection_id)

# 根据配置创建识别器
self.sense_voice_service.create_recognizer(
language=config.get("language", "auto"),
use_itn=config.get("use_itn", True)
)

# 或者创建连接专属的识别器
recognizer = self.sense_voice_service.create_streaming_recognizer(
language=config.get("language", "auto"),
use_itn=config.get("use_itn", True)
)

🎨 界面功能详解
1. 控制面板
开始录音按钮: 启动麦克风和识别服务
停止录音按钮: 停止录音并清理资源
清空结果按钮: 清除所有识别结果记录
2. 设置面板
语言选择: 🚫 当前假功能
逆文本标准化: 🚫 当前假功能
3. 状态面板
连接状态: 显示 WebSocket 连接状态
录音状态: 显示当前是否在录音
音频质量: 显示音频输入质量评估
4. 结果显示
实时结果: 显示当前正在说话的识别结果（partial）
最终结果: 显示完成的句子识别结果（final）
统计信息: 显示段落数量和字数统计
5. 消息系统
错误消息: 红色提示框，显示连接错误等严重问题
警告消息: 黄色提示框，显示音频质量问题等警告
信息消息: 蓝色提示框，显示连接成功等信息

📱 用户体验优化
1. 自动重连机制
网络断线时自动尝试重连
最多重试 5 次，间隔 3 秒
用户可看到重连进度
2. 权限处理
友好的麦克风权限请求提示
详细的各种错误情况处理：
NotAllowedError: “请允许使用麦克风权限”
NotFoundError: “未找到麦克风设备”
3. 页面状态管理
页面隐藏时提示用户录音可能受影响
页面关闭时自动清理资源
防止内存泄漏

🚀 后期功能扩展建议
1. 激活假功能
1. 语言选择：实现真正的多语言识别
2. 逆文本标准化：允许用户选择是否启用
3. VAD 参数调节：添加敏感度调节滑块
2. 新增功能
1. 语音合成 (TTS)：添加文字转语音功能
2. 对话模式：实现语音对话交互
3. 历史记录：保存识别历史和搜索功能
4. 导出功能：支持导出文本、SRT字幕等格式
3. 性能优化
1. 压缩传输：音频数据压缩减少带宽
2. 本地缓存：离线使用和缓存优化
3. PWA 支持：支持离线安装使用



