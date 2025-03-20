import asyncio
import websockets
import requests
import json
import os

# 從環境變數獲取配置
MORALIS_API_KEY = os.getenv("MORALIS_API_KEY")
BITQUERY_API_KEY = os.getenv("BITQUERY_API_KEY")
ETHERSCAN_API_KEY = os.getenv("ETHERSCAN_API_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
THRESHOLD_USD = 500000  # 提高到 50 萬美元
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
        response = requests.get(url)
        if response.status_code == 200:
            PRICE_CACHE["ETH"] = response.json()["ethereum"]["usd"]
        await asyncio.sleep(60)

# 測試函數：檢查 API 並發送測試訊息
async def test_api():
    await send_telegram_message("🚀 程式啟動，正在測試所有 API...")

    # 測試 Moralis
    try:
        headers = {"x-api-key": MORALIS_API_KEY}
        response = requests.get("https://deep-index.moralis.io/api/v2.2/info", headers=headers)
        await send_telegram_message("✅ Moralis API 測試成功" if response.status_code == 200 else f"❌ Moralis API 測試失敗：{response.status_code}")
    except Exception as e:
        await send_telegram_message(f"❌ Moralis API 測試錯誤：{e}")

    # 測試 Bitquery
    try:
        url = "https://graphql.bitquery.io/"
        query = "{ EVM(network: eth) { Blocks(limit: {count: 1}) { Hash } } }"
        response = requests.post(url, json={"query": query}, headers={"X-API-KEY": BITQUERY_API_KEY})
        await send_telegram_message("✅ Bitquery API 測試成功" if response.status_code == 200 else f"❌ Bitquery API 測試失敗：{response.status_code}")
    except Exception as e:
        await send_telegram_message(f"❌ Bitquery API 測試錯誤：{e}")

    # 測試 Public
