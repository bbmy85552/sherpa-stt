import requests
import os
from dotenv import load_dotenv
import time
import json
import logging
from datetime import datetime
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import MINIMAX_CONFIG, TTS_CONFIG, SYSTEM_PROMPT, LOG_CONFIG

load_dotenv()

# 配置日志
log_filename = f"minimax_test_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
logging.basicConfig(
    level=getattr(logging, LOG_CONFIG["level"]),
    format=LOG_CONFIG["format"],
    handlers=[
        logging.FileHandler(log_filename, encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger()

# API配置
api_key = os.environ.get("MINIMAX_API_KEY")

if not api_key:
    raise ValueError("MINIMAX_API_KEY not found in environment variables")

# 请求头
headers = {"Authorization": f"Bearer {api_key}"}
tts_headers = {
    "Authorization": f"Bearer {api_key}",
    "Content-Type": "application/json"
}

# 请求载荷
payload = {
    "model": MINIMAX_CONFIG["model"],
    "messages": [
        {
            "role": "user",
            "name": "user",
            "content": SYSTEM_PROMPT
        },
    ],
    "stream": MINIMAX_CONFIG["stream"],
    "max_tokens": MINIMAX_CONFIG["max_tokens"],
    "temperature": MINIMAX_CONFIG["temperature"],
}
logger.info("开始MiniMax API单次测试运行")
logger.info("=== 单次运行 ===")
start_time = time.time()
response = requests.post(MINIMAX_CONFIG["api_url"], headers=headers, json=payload)
response.raise_for_status()
text_response_data = response.json()
print(text_response_data)
print("11311", text_response_data['choices'][0]['message']['content'])
res = text_response_data['choices'][0]['message']['content']

# 记录响应内容
logger.info(f"响应内容: {res}")

# TTS请求载荷，使用配置中的设置
data = TTS_CONFIG.copy()
data["text"] = res

# Make the POST request
tts_response = requests.post(MINIMAX_CONFIG["tts_url"], headers=tts_headers, json=data)
parsed_json = json.loads(tts_response.text)
# 记录TTS响应时间
end_time = time.time()

# get audio
audio_value = bytes.fromhex(parsed_json['data']['audio'])

# 按audio+时间来命名
filename = f"block_audio_{int(time.time())}.mp3"
with open(filename, 'wb') as f:
    f.write(audio_value)
response_time = end_time - start_time
print(f"Response Time: {response_time:.3f} seconds")

# 记录响应时间和输出长度
logger.info(f"响应时间: {response_time:.3f} 秒")
logger.info(f"输出长度: {len(res)} 字符")
logger.info(f"音频文件已保存为: {filename}")
logger.info("单次测试运行完成")