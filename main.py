from flask import Flask, request, jsonify
import requests, hmac, hashlib, time, json, os

app = Flask(__name__)

API_KEY = os.environ.get("BYBIT_API_KEY")
API_SECRET = os.environ.get("BYBIT_API_SECRET")
BASE_URL = "https://api.bybit.com"

LEVERAGE = 5
TP_PCT = 0.06
SL_PCT = 0.08

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json
    print("Received:", data)

    symbol = data.get("symbol", "BTCUSDT")
    side = data.get("side", "Buy")

    balance = get_balance()
    entry_price = get_price(symbol)
    qty = round((balance * LEVERAGE) / entry_price, 3)

    if side.lower() == "buy":
        tp = round(entry_price * (1 + TP_PCT), 2)
        sl = round(entry_price * (1 - SL_PCT), 2)
    else:
        tp = round(entry_price * (1 - TP_PCT), 2)
        sl = round(entry_price * (1 + SL_PCT), 2)

    payload = {
        "category": "linear",
        "symbol": symbol,
        "side": side,
        "orderType": "Market",
        "qty": str(qty),
        "takeProfit": str(tp),
        "stopLoss": str(sl),
        "timeInForce": "GoodTillCancel"
    }

    return place_order(payload)

def get_balance():
    ts = str(int(time.time() * 1000))
    sign = sign_request(ts, "", "")
    headers = {
        "X-BYBIT-API-KEY": API_KEY,
        "X-BYBIT-SIGN": sign,
        "X-BYBIT-TIMESTAMP": ts
    }
    url = f"{BASE_URL}/v5/account/wallet-balance?accountType=UNIFIED"
    r = requests.get(url, headers=headers).json()
    return float(r["result"]["list"][0]["totalEquity"])

def get_price(symbol):
    url = f"{BASE_URL}/v5/market/tickers?category=linear&symbol={symbol}"
    r = requests.get(url).json()
    return float(r["result"]["list"][0]["lastPrice"])

def place_order(order_data):
    ts = str(int(time.time() * 1000))
    body = json.dumps(order_data)
    sign = sign_request(ts, body, "")
    headers = {
        "X-BYBIT-API-KEY": API_KEY,
        "X-BYBIT-SIGN": sign,
        "X-BYBIT-TIMESTAMP": ts,
        "Content-Type": "application/json"
    }
    r = requests.post(BASE_URL + "/v5/order/create", headers=headers, data=body)
    return jsonify(r.json())

def sign_request(ts, body, recv_window):
    message = f"{ts}{API_KEY}{recv_window}{body}"
    return hmac.new(bytes(API_SECRET, "utf-8"), bytes(message, "utf-8"), hashlib.sha256).hexdigest()

if __name__ == '__main__':
    app.run()

