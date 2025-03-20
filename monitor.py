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
THRESHOLD_USD = 100000
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
    payload = {
        "chat_id": CHAT_ID,
        "text": message
    }
    try:
        response = requests.post(url, json=payload)
        if response.status_code != 200:
            print(f"Telegram 發送失敗：{response.text}")
    except Exception as e:
        print(f"Telegram 發送錯誤：{e}")

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
        response = requests.get("https://deep-index.moralis.io/api/v2/block/latest/transactions?chain=eth", headers=headers)
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

    # 測試 PublicNode
    try:
        async with websockets.connect("wss://ethereum.publicnode.com") as ws:
            await ws.send(json.dumps({"id": 1, "jsonrpc": "2.0", "method": "eth_blockNumber", "params": []}))
            response = await ws.recv()
            await send_telegram_message("✅ PublicNode API 測試成功" if json.loads(response).get("result") else "❌ PublicNode API 測試失敗")
    except Exception as e:
        await send_telegram_message(f"❌ PublicNode API 測試錯誤：{e}")

    # 測試 Binance API
    try:
        response = requests.get("https://api.binance.com/api/v3/trades?symbol=BTCUSDT&limit=1")
        await send_telegram_message("✅ Binance API 測試成功" if response.status_code == 200 else f"❌ Binance API 測試失敗：{response.status_code}")
    except Exception as e:
        await send_telegram_message(f"❌ Binance API 測試錯誤：{e}")

    # 測試 Etherscan
    try:
        url = f"https://api.etherscan.io/api?module=proxy&action=eth_blockNumber&apikey={ETHERSCAN_API_KEY}"
        response = requests.get(url)
        await send_telegram_message("✅ Etherscan API 測試成功" if response.status_code == 200 and response.json()["result"] else f"❌ Etherscan API 測試失敗：{response.status_code}")
    except Exception as e:
        await send_telegram_message(f"❌ Etherscan API 測試錯誤：{e}")

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
                        await send_telegram_message(f"🚨 DEX 大額交易 (Moralis)：{value_eth} ETH (${usd_value})\n哈希：{tx['hash']}")
        except Exception as e:
            print(f"Moralis 錯誤：{e}")
        await asyncio.sleep(5)

# DEX 監控 - Bitquery
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
          Trade { Buy { Amount AmountInUSD Currency { Symbol } } }
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
                    await send_telegram_message(f"🚨 DEX 大額交易 (Bitquery)：${amount_usd}\n哈希：{tx_hash}")
        except Exception as e:
            print(f"Bitquery 錯誤：{e}")
        await asyncio.sleep(60)

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
                await ws.recv()
                while True:
                    message = await ws.recv()
                    block_data = json.loads(message)
                    block_number = block_data["params"]["result"]["number"]
                    block_url = "https://ethereum.publicnode.com"
                    block_payload = {"id": 1, "jsonrpc": "2.0", "method": "eth_getBlockByNumber", "params": [block_number, True]}
                    response = requests.post(block_url, json=block_payload)
                    if response.status_code == 200:
                        block = response.json()["result"]
                        for tx in block["transactions"]:
                            value_wei = int(tx["value"], 16)
                            value_eth = value_wei / 10**18
                            usd_value = value_eth * PRICE_CACHE.get("ETH", 0)
                            if usd_value > THRESHOLD_USD:
                                await send_telegram_message(f"🚨 DEX/鏈上大額轉帳 (PublicNode)：{value_eth} ETH (${usd_value})\n哈希：{tx['hash']}")
        except Exception as e:
            print(f"PublicNode 錯誤：{e}")
            await asyncio.sleep(5)

# CEX 監控 - Binance API
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
                        await send_telegram_message(f"🚨 CEX 大額交易 (Binance)：{qty} BTC (${usd_value})\nID：{trade['id']}")
        except Exception as e:
            print(f"Binance 錯誤：{e}")
        await asyncio.sleep(10)

# CEX 監控 - Etherscan
async def monitor_cex_etherscan():
    address = "0x3f5ce5fbfe3e9af3971dd833d26ba9b5c936f0be"
    url = f"https://api.etherscan.io/api?module=account&action=txlist&address={address}&sort=desc&apikey={ETHERSCAN_API_KEY}"
    while True:
        try:
            response = requests.get(url)
            if response.status_code == 200:
                for tx in response.json()["result"][:10]:
                    value_wei = int(tx["value"])
                    value_eth = value_wei / 10**18
                    usd_value = value_eth * PRICE_CACHE.get("ETH", 0)
                    if usd_value > THRESHOLD_USD:
                        await send_telegram_message(f"🚨 CEX 鏈上活動 (Etherscan)：{value_eth} ETH (${usd_value})\n哈希：{tx['hash']}")
        except Exception as e:
            print(f"Etherscan 錯誤：{e}")
        await asyncio.sleep(60)

# 主函數：先測試再監控
async def main():
    await send_telegram_message("🚀 程式啟動，正在測試所有 API...")
    await test_api()
    await send_telegram_message("✅ 測試完成，開始正常監控")
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
