import asyncio
import websockets
import requests
import json
import os
from http.server import HTTPServer, BaseHTTPRequestHandler

# 從環境變數獲取配置
MORALIS_API_KEY = os.getenv("MORALIS_API_KEY")
BITQUERY_API_KEY = os.getenv("BITQUERY_API_KEY")
ETHERSCAN_API_KEY = os.getenv("ETHERSCAN_API_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
THRESHOLD_USD = 500000  # 門檻設為 50 萬美元
PRICE_CACHE = {}

# 檢查環境變數是否設置
required_vars = {
    "MORALIS_API_KEY": MORALIS_API_KEY,
    "BITQUERY_API_KEY": BITQUERY_API_KEY,
    "ETHERSCAN_API_KEY": ETHERSCAN_API_KEY,
    "TELEGRAM_TOKEN": TELEGRAM_TOKEN,
    "CHAT_ID": CHAT_ID
}
for var_name, var_value in required_vars.items():
    if not var_value:
        raise ValueError(f"環境變數 {var_name} 未設置，請在 Render 的 Environment 中配置")

# Telegram POST 發送函數
async def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message}
    try:
        response = requests.post(url, json=payload)
        if response.status_code != 200:
            print(f"Telegram 發送失敗：{response.text}")
    except Exception as e:
        print(f"Telegram 發送錯誤：{e}")

# 獲取地址餘額（Etherscan）
def get_address_balance(address):
    url = f"https://api.etherscan.io/api?module=account&action=balance&address={address}&tag=latest&apikey={ETHERSCAN_API_KEY}"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            balance_wei = int(response.json()["result"])
            return balance_wei / 10**18
        return None
    except Exception:
        return None

# 更新價格（CoinGecko）
async def update_prices():
    while True:
        url = "https://api.coingecko.com/api/v3/simple/price?ids=ethereum&vs_currencies=usd"
        response = requests
