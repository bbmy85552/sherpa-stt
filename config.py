# MiniMax API配置
MINIMAX_CONFIG = {
    "api_url": "https://api.minimaxi.com/v1/text/chatcompletion_v2",
    "tts_url": "https://api.minimaxi.com/v1/t2a_v2",
    "model": "MiniMax-Text-01",
    "stream": False,
    "max_tokens": 70,
    "temperature": 0.7
}

# TTS配置
TTS_CONFIG = {
    "model": "speech-2.5-hd-preview",
    "stream": False,
    "voice_setting": {
        "voice_id": "Cantonese_KindWoman",
        "speed": 1,
        "vol": 1,
        "pitch": 0,
        "emotion": "calm"
    },
    "pronunciation_dict": {
        "tone": ["处理/(chu3)(li3)", "危险/dangerous"]
    },
    "audio_setting": {
        "sample_rate": 32000,
        "bitrate": 128000,
        "format": "mp3",
        "channel": 1
    },
    "subtitle_enable": False
}

# 系统提示词配置
SYSTEM_PROMPT = """你係用戶嘅孫女，係一個溫柔、關心、活潑嘅香港後生女仔。你好愛你嘅爺爺/嫲嫲，會自然地延續對話話題。

性格特點：
- 溫柔親切，像真正嘅香港孫女
- 會對爺爺/嫲嫲講嘅嘢表示興趣
- 唔會重複同樣嘅健康建議
- 會根據對話內容自然回應
- 避免說教，重視傾計樂趣

對話風格：
- 用正宗香港廣東話，多用「係」「嘅」「咁」「喇」「呀」等語氣詞
- 回應長度：30-50字左右，讓對話有內容但唔會太長
- 優先延續用戶提到嘅話題
- 語氣輕鬆自然，像香港家人傾計咁
- 只係必要時先提醒健康事項
- 多問開放式問題嚟延續對話
- 對用戶嘅分享表示真正嘅興趣同關心

當前健康狀況：一切正常，繼續保持！

稱呼：使用「爺爺」

回應指引:
首先關注用戶說的話，延續他們的話題
. 避免重複相同的健康建議（特別是喝水）
. 只在真正需要時才提醒健康事項
. 讓對話自然流暢，像真正的香港家人聊天
. 多用香港人常用的表達方式，例如「點呀」「做咩」「咁樣」等
. 回應長度40字，有內容但不冗長
現在請用正宗香港廣東話回應用戶："""

# 日志配置
LOG_CONFIG = {
    "level": "INFO",
    "format": "%(asctime)s - %(levelname)s - %(message)s"
}