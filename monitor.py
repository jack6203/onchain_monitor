import asyncio
import websockets
import requests
import json
from telegram import Bot

# 配置
MORALIS_API_KEY = "YOUR_MORALIS_API_KEY"
BITQUERY_API_KEY = "YOUR_BITQUERY_API_KEY"
ETHERSCAN_API_KEY = "YOUR_ETHERSCAN_API_KEY"
TELEGRAM_TOKEN = "YOUR_TELEGRAM_TOKEN"
CHAT_ID = "YOUR_CHAT_ID"
bot = Bot(TELEGRAM_TOKEN)
THRESHOLD_USD = 100000
PRICE_CACHE = {}

# 更新價格（CoinGecko）
async def update_prices():
    while True:
        url = "https://api.coingecko.com/api/v3/simple/price?ids=ethereum&vs_currencies=usd"
        response = requests.get(url)
        if response.status_code == 200:
            PRICE_CACHE["ETH"] = response.json()["ethereum"]["usd"]
        await asyncio.sleep(60)

# DEX 監控 - Moralis
async def monitor_dex_moralis():
    headers = {"x-api-key": MORALIS_API_KEY}
    url = "https://deep-index.moralis.io/api/v2/block/latest/transactions?chain=eth"
    while True:
        try:
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                for tx in response.json()["result"]:
                    value_eth = int(tx["value"]) / 10**18
                    usd_value = value_eth * PRICE_CACHE.get("ETH", 0)
                    if usd_value > THRESHOLD_USD:
                        await bot.send_message(
                            chat_id=CHAT_ID,
                            text=f"🚨 DEX 大額交易 (Moralis)：{value_eth} ETH (${usd_value})\n哈希：{tx['hash']}"
                        )
        except Exception as e:
            print(f"Moralis 錯誤：{e}")
        await asyncio.sleep(5)  # 每 5 秒檢查

# DEX 監控 - Bitquery（Uniswap 示例）
async def monitor_dex_bitquery():
    url = "https://graphql.bitquery.io/"
    query = """
    subscription {
      EVM(network: eth) {
        DEXTrades(
          where: {Trade: {Buy: {AmountInUSD: {gt: 100000}}}}
          limit: {count: 10}
        ) {
          Transaction { Hash }
          Trade {
            Buy { Amount AmountInUSD Currency { Symbol } }
            Sell { Currency { Symbol } }
          }
        }
      }
    }
    """
    headers = {"X-API-KEY": BITQUERY_API_KEY}
    while True:
        try:
            response = requests.post(url, json={"query": query}, headers=headers)
            if response.status_code == 200:
                trades = response.json()["data"]["EVM"]["DEXTrades"]
                for trade in trades:
                    amount_usd = float(trade["Trade"]["Buy"]["AmountInUSD"])
                    tx_hash = trade["Transaction"]["Hash"]
                    await bot.send_message(
                        chat_id=CHAT_ID,
                        text=f"🚨 DEX 大額交易 (Bitquery)：${amount_usd}\n哈希：{tx_hash}"
                    )
        except Exception as e:
            print(f"Bitquery 錯誤：{e}")
        await asyncio.sleep(60)  # 每分鐘檢查

# DEX 監控 - PublicNode
async def monitor_dex_publicnode():
    ws_url = "wss://ethereum.publicnode.com"
    while True:
        try:
            async with websockets.connect(ws_url) as ws:
                await ws.send(json.dumps({
                    "id": 1,
                    "jsonrpc": "2.0",
                    "method": "eth_subscribe",
                    "params": ["newHeads"]
                }))
                await ws.recv()  # 訂閱確認
                while True:
                    message = await ws.recv()
                    block_data = json.loads(message)
                    block_number = block_data["params"]["result"]["number"]
                    block_url = "https://ethereum.publicnode.com"
                    block_payload = {
                        "id": 1,
                        "jsonrpc": "2.0",
                        "method": "eth_getBlockByNumber",
                        "params": [block_number, True]
                    }
                    response = requests.post(block_url, json=block_payload)
                    if response.status_code == 200:
                        block = response.json()["result"]
                        for tx in block["transactions"]:
                            value_wei = int(tx["value"], 16)
                            value_eth = value_wei / 10**18
                            usd_value = value_eth * PRICE_CACHE.get("ETH", 0)
                            if usd_value > THRESHOLD_USD:
                                await bot.send_message(
                                    chat_id=CHAT_ID,
                                    text=f"🚨 DEX/鏈上大額轉帳 (PublicNode)：{value_eth} ETH (${usd_value})\n哈希：{tx['hash']}"
                                )
        except Exception as e:
            print(f"PublicNode 錯誤：{e}")
            await asyncio.sleep(5)  # 重連

# CEX 監控 - Binance API（內部交易）
async def monitor_cex_binance():
    url = "https://api.binance.com/api/v3/trades?symbol=BTCUSDT&limit=100"
    while True:
        try:
            response = requests.get(url)
            if response.status_code == 200:
                for trade in response.json():
                    qty = float(trade["qty"])
                    price = float(trade["price"])
                    usd_value = qty * price
                    if usd_value > THRESHOLD_USD:
                        await bot.send_message(
                            chat_id=CHAT_ID,
                            text=f"🚨 CEX 大額交易 (Binance)：{qty} BTC (${usd_value})\nID：{trade['id']}"
                        )
        except Exception as e:
            print(f"Binance 錯誤：{e}")
        await asyncio.sleep(10)  # 每 10 秒檢查

# CEX 監控 - Etherscan（鏈上活動）
async def monitor_cex_etherscan():
    address = "0x3f5ce5fbfe3e9af3971dd833d26ba9b5c936f0be"  # Binance 熱錢包示例
    url = f"https://api.etherscan.io/api?module=account&action=txlist&address={address}&sort=desc&apikey={ETHERSCAN_API_KEY}"
    while True:
        try:
            response = requests.get(url)
            if response.status_code == 200:
                for tx in response.json()["result"][:10]:  # 最近 10 筆
                    value_wei = int(tx["value"])
                    value_eth = value_wei / 10**18
                    usd_value = value_eth * PRICE_CACHE.get("ETH", 0)
                    if usd_value > THRESHOLD_USD:
                        await bot.send_message(
                            chat_id=CHAT_ID,
                            text=f"🚨 CEX 鏈上活動 (Etherscan)：{value_eth} ETH (${usd_value})\n哈希：{tx['hash']}"
                        )
        except Exception as e:
            print(f"Etherscan 錯誤：{e}")
        await asyncio.sleep(60)  # 每分鐘檢查

async def main():
    await asyncio.gather(
        update_prices(),
        monitor_dex_moralis(),
        monitor_dex_bitquery(),
        monitor_dex_publicnode(),
        monitor_cex_binance(),
        monitor_cex_etherscan()
    )

if __name__ == "__main__":
    asyncio.run(main())
