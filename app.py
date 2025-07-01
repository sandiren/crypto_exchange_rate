from flask import Flask, render_template, request, jsonify
import requests, json, os, time
from dotenv import load_dotenv

load_dotenv()
CURRENCY_API_KEY = os.getenv("CURRENCYLAYER_API_KEY")
EXCHANGERATE_API_KEY = os.getenv("EXCHANGERATE_API_KEY")
app = Flask(__name__)

# CoinGecko cache
COIN_MAP_CACHE = {}
COIN_MAP_LAST_UPDATED = 0
CACHE_TTL_SECONDS = 600

# Load fiat metadata
FIAT_META_FILE = "currency_metadata.json"
if not os.path.exists(FIAT_META_FILE):
    raise FileNotFoundError("currency_metadata.json missing")
with open(FIAT_META_FILE, "r") as f:
    fiat_map = json.load(f)


def get_crypto_map():
    global COIN_MAP_CACHE, COIN_MAP_LAST_UPDATED
    if not COIN_MAP_CACHE or (time.time() - COIN_MAP_LAST_UPDATED > CACHE_TTL_SECONDS):
        try:
            res = requests.get("https://api.coingecko.com/api/v3/coins/markets", params={
                "vs_currency": "usd",
                "order": "market_cap_desc",
                "per_page": 100,
                "page": 1
            })
            coins = res.json()
            COIN_MAP_CACHE = {c["id"].lower(): {"name": c["name"], "image": c["image"]} for c in coins}
            COIN_MAP_LAST_UPDATED = time.time()
        except Exception as e:
            print("❌ Failed to fetch crypto list:", e)
            COIN_MAP_CACHE = {}
    return COIN_MAP_CACHE


def get_usd_to_fiat(fiat_code):
    fiat_code = fiat_code.upper()

    if CURRENCY_API_KEY:
        try:
            url = "http://api.currencylayer.com/live"
            res = requests.get(url, params={
                "access_key": CURRENCY_API_KEY,
                "currencies": fiat_code,
                "format": 1
            })
            data = res.json()
            if data.get("success") and f"USD{fiat_code}" in data["quotes"]:
                return float(data["quotes"][f"USD{fiat_code}"])
        except Exception as e:
            print("⚠️ CurrencyLayer failed:", e)

    if EXCHANGERATE_API_KEY:
        try:
            res = requests.get("https://api.apilayer.com/exchangerates_data/latest", headers={
                "apikey": EXCHANGERATE_API_KEY
            }, params={
                "base": "USD",
                "symbols": fiat_code
            })
            data = res.json()
            if "rates" in data and fiat_code in data["rates"]:
                return float(data["rates"][fiat_code])
        except Exception as e:
            print("⚠️ ExchangeRate API failed:", e)

    try:
        res = requests.get(f"https://api.exchangerate.host/latest?base=USD&symbols={fiat_code}")
        data = res.json()
        if data.get("success") and fiat_code in data["rates"]:
            return float(data["rates"][fiat_code])
    except Exception as e:
        print("⚠️ Fallback (exchangerate.host) failed:", e)

    return None


def get_fiat_to_usd(fiat_code):
    rate = get_usd_to_fiat(fiat_code)
    return 1 / rate if rate else None


@app.route("/")
def home():
    coin_map = get_crypto_map()
    return render_template("index.html", coin_map=coin_map, fiat_map=fiat_map)


@app.route("/convert", methods=["GET"])
def convert():
    coin_map = get_crypto_map()
    fiat_codes = {code.lower() for code in fiat_map.keys()}

    base_raw = request.args.get("base", "").strip().lower()
    target_raw = request.args.get("target", "").strip().lower()
    try:
        amount = float(request.args.get("amount", 1))
    except:
        return jsonify({"error": "Invalid amount"}), 400

    is_base_crypto = base_raw in coin_map
    is_target_crypto = target_raw in coin_map
    is_base_fiat = base_raw in fiat_codes
    is_target_fiat = target_raw in fiat_codes

    print(f"\n🔍 Attempting conversion: {amount} {base_raw} → {target_raw}")

    # Direct lookup
    price_direct = None
    source = "direct"
    try:
        crypto_id = base_raw if is_base_crypto else target_raw
        fiat_code = target_raw if is_target_fiat else base_raw
        res = requests.get("https://api.coingecko.com/api/v3/simple/price", params={
            "ids": crypto_id,
            "vs_currencies": fiat_code
        })
        data = res.json()
        price_direct = data.get(crypto_id, {}).get(fiat_code)
    except Exception as e:
        print("⚠️ Direct price fetch failed:", e)

    # Fallback via USD
    if price_direct is None:
        print("❌ Direct not found, trying USD fallback...")
        try:
            if is_base_crypto and is_target_fiat:
                crypto_id = base_raw
                fiat_code = target_raw.upper()
                usd_price = requests.get("https://api.coingecko.com/api/v3/simple/price", params={
                    "ids": crypto_id,
                    "vs_currencies": "usd"
                }).json().get(crypto_id, {}).get("usd")

                usd_to_fiat = get_usd_to_fiat(fiat_code)
                print(f"🧾 usd_price = {usd_price}")
                print(f"💱 usd_to_fiat = {usd_to_fiat}")

                if usd_price and usd_to_fiat:
                    price_direct = usd_price * usd_to_fiat
                    source = "via_usd"
                else:
                    raise ValueError("Missing usd or fiat rate")

            elif is_base_fiat and is_target_crypto:
                crypto_id = target_raw
                fiat_code = base_raw.upper()
                usd_price = requests.get("https://api.coingecko.com/api/v3/simple/price", params={
                    "ids": crypto_id,
                    "vs_currencies": "usd"
                }).json().get(crypto_id, {}).get("usd")

                fiat_to_usd = get_fiat_to_usd(fiat_code)
                print(f"🧾 usd_price = {usd_price}")
                print(f"💱 fiat_to_usd = {fiat_to_usd}")

                if usd_price and fiat_to_usd:
                    price_direct = fiat_to_usd / usd_price
                    source = "via_usd"
                else:
                    raise ValueError("Missing usd or fiat rate")
            else:
                return jsonify({"error": "Invalid currency pair"}), 400

        except Exception as e:
            print("❌ Fallback failed:", e)
            return jsonify({"error": "Conversion failed"}), 400

    converted = round(price_direct * amount, 6)

    history = []
    try:
        hist_crypto = base_raw if is_base_crypto else target_raw
        hist_currency = target_raw if is_target_fiat else base_raw

        hist_url = f"https://api.coingecko.com/api/v3/coins/{hist_crypto}/market_chart"
        hist_res = requests.get(hist_url, params={"vs_currency": hist_currency, "days": 7})
        hist_data = hist_res.json().get("prices", [])
        history = [[t, round(p, 4)] for t, p in hist_data]
    except Exception as e:
        print("⚠️ History fetch failed:", e)

    return jsonify({
        "converted": converted,
        "price": round(price_direct, 6),
        "history": history,
        "source": source
    })


if __name__ == "__main__":
    app.run(debug=True)