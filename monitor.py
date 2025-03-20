import asyncio
import requests
from telegram import Bot

# 配置
MORALIS_API_KEY = "YOUR_MORALIS_API_KEY"
WHALE_API_KEY = "YOUR_WHALE_API_KEY"
TELEGRAM_TOKEN = "YOUR_TELEGRAM_TOKEN"
CHAT_ID = "YOUR_CHAT_ID"
bot = Bot(TELEGRAM_TOKEN)
THRESHOLD_USD = 100000

# DEX 監控（Moralis）
async def monitor_dex():
    headers = {"x-api-key": MORALIS_API_KEY}
    url = "https://deep-index.moralis.io/api/v2/block/latest/transactions?chain=eth"
    while True:
        try:
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                for tx in response.json()["result"]:
                    value_eth = int(tx["value"]) / 10**18
                    usd_value = value_eth * requests.get("https://api.coingecko.com/api/v3/simple/price?ids=ethereum&vs_currencies=usd").json()["ethereum"]["usd"]
                    if usd_value > THRESHOLD_USD:
                        await bot.send_message(
                            chat_id=CHAT_ID,
                            text=f"🚨 DEX 大額交易：{value_eth} ETH (${usd_value})\n哈希：{tx['hash']}"
                        )
        except Exception as e:
            print(f"DEX 錯誤：{e}")
        await asyncio.sleep(5)  # 每 5 秒檢查

# CEX 監控（Whale Alert）
async def monitor_cex():
    url = f"https://api.whale-alert.io/v1/transactions?api_key={WHALE_API_KEY}&min_value=100000"
    while True:
        try:
            response = requests.get(url)
            if response.status_code == 200:
                for tx in response.json()["transactions"]:
                    amount_usd = tx["amount_usd"]
                    from_addr = tx["from"]["address"]
                    to_addr = tx["to"]["address"]
                    tx_hash = tx["hash"]
                    await bot.send_message(
                        chat_id=CHAT_ID,
                        text=f"🚨 CEX 大額轉帳：${amount_usd}\n從：{from_addr}\n到：{to_addr}\n哈希：{tx_hash}"
                    )
        except Exception as e:
            print(f"CEX 錯誤：{e}")
        await asyncio.sleep(60)  # 每分鐘檢查

async def main():
    await asyncio.gather(monitor_dex(), monitor_cex())

if __name__ == "__main__":
    asyncio.run(main())
