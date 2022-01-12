import os

from dotenv import load_dotenv

load_dotenv()

# Binance
BINANCE_TESTNET_BASE_URL = "https://testnet.binancefuture.com"
BINANCE_TESTNET_WS_URL = "wss://stream.binancefuture.com/ws"
BINANCE_BASE_URL = "https://fapi.binance.com"
BINANCE_WS_URL = "wss://fstream.binance.com/ws"

BINANCE_CONTRACTS_URL = "/fapi/v1/exchangeInfo"
BINANCE_HISTORIC_CANDLES_URL = "/fapi/v1/klines"
BINANCE_BID_ASK_URL = "/fapi/v1/ticker/bookTicker"
BINANCE_ORDER_URL = "/fapi/v1/order"
BINANCE_ACCOUNT_URL = "/fapi/v1/account"

BINANCE_TESTNET_API_KEY = os.environ.get("BINANCE_TESTNET_API_KEY")
BINANCE_TESTNET_API_SECRET = os.environ.get("BINANCE_TESTNET_API_SECRET")

# Bitmex
BITMEX_TESTNET_BASE_URL = "https://testnet.bitmex.com"
BITMEX_TESTNET_WS_URL = "wss://testnet.bitmex.com/realtime"
BITMEX_BASE_URL = "https://www.bitmex.com/api/v1"
BITMEX_WS_URL = "wss://www.bitmex.com/realtime"

BITMEX_TESTNET_API_KEY = os.environ.get("BITMEX_TESTNET_API_KEY")
BITMEX_TESTNET_API_SECRET = os.environ.get("BITMEX_TESTNET_API_SECRET")

BITMEX_CONTRACTS_URL = "/api/v1/instrument/active"
BITMEX_BALANCES_URL = "/api/v1/user/margin"
BITMEX_HISTORIC_CANDLES_URL = "/api/v1/trade/bucketed"
BITMEX_ORDER_URL = "/api/v1/order"
