diff --git a//dev/null b/README.md
index 0000000000000000000000000000000000000000..f4e1331bb8f08d7beffb4204264d4723c8f30065 100644
--- a//dev/null
+++ b/README.md
@@ -0,0 +1,39 @@
+# Crypto Exchange Rate
+
+This project is a simple Flask application that converts between cryptocurrencies and fiat currencies. It fetches data from the CoinGecko API and uses optional third party services for fiat exchange rates.
+
+## Environment Variables
+
+The application reads the following variables from the environment (or a `.env` file):
+
+- `CURRENCYLAYER_API_KEY` – API key for [CurrencyLayer](https://currencylayer.com/). Used for fiat exchange rates.
+- `EXCHANGERATE_API_KEY` – API key for the [ExchangeRate](https://apilayer.com/marketplace/exchangerates_data-api) service. Also used for fiat exchange rates.
+
+At least one of the keys above should be provided in order to convert between crypto and fiat currencies.
+
+## Setup and Running
+
+1. **Create a virtual environment and install dependencies**
+
+```bash
+python3 -m venv venv
+source venv/bin/activate
+pip install Flask requests python-dotenv
+```
+
+2. **Configure environment variables**
+
+Set the API keys as environment variables or place them in a `.env` file in the project root:
+
+```bash
+CURRENCYLAYER_API_KEY=your_currencylayer_key
+EXCHANGERATE_API_KEY=your_exchangerate_key
+```
+
+3. **Run the Flask app**
+
+```bash
+python app.py
+```
+
+The application will start on `http://127.0.0.1:5000/` and you can access the converter interface in your browser.
