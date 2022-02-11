import hashlib
import hmac
import json
import logging
import threading
import time
from typing import Dict, Optional, List, Union
from urllib.parse import urlencode

import requests
import websocket

from constants import (
    BINANCE_TESTNET_BASE_URL,
    BINANCE_BASE_URL,
    BINANCE_CONTRACTS_URL,
    BINANCE_HISTORIC_CANDLES_URL,
    BINANCE_BID_ASK_URL,
    BINANCE_ORDER_URL,
    BINANCE_ACCOUNT_URL,
    BINANCE_TESTNET_WS_URL,
    BINANCE_WS_URL,
)
from helpers.Exchange import Exchange
from helpers.Methods import Methods
from models.Balance import Balance
from models.Candle import Candle
from models.Contract import Contract
from models.OrderStatus import OrderStatus
from strategies.BreakoutStrategy import BreakoutStrategy
from strategies.TechnicalStrategy import TechnicalStrategy

logger = logging.getLogger()


class BinanceFuturesClient:
    def __init__(self, public_key: str, private_key: str, testnet: bool) -> None:
        if testnet:
            self._base_url = BINANCE_TESTNET_BASE_URL
            self._wss_url = BINANCE_TESTNET_WS_URL
        else:
            self._base_url = BINANCE_BASE_URL
            self._wss_url = BINANCE_WS_URL

        self._public_key = public_key
        self._private_key = private_key

        self._headers = {"X-MBX-APIKEY": self._public_key}

        self.contracts = self.get_contracts()
        self.balances = self.get_balances()

        self.prices = dict()
        self.strategies: Dict[int, Union[TechnicalStrategy, BreakoutStrategy]] = dict()

        self.logs = []
        self._ws_id = 1
        self._ws = None

        t = threading.Thread(target=self._start_ws)
        t.start()

        logger.info("Binance futures client successfully initialized")

    def _add_logs(self, msg: str):
        logger.info("%s", msg)
        self.logs.append({"log": msg, "displayed": False})

    def _generate_signature(self, data: Dict) -> str:
        return hmac.new(
            self._private_key.encode(),
            urlencode(data).encode(),
            hashlib.sha256,
        ).hexdigest()

    def _make_request(self, method: Methods, endpoint: str, data: Optional[Dict]):
        if method == Methods.GET:
            try:
                response = requests.get(
                    f"{self._base_url}{endpoint}",
                    params=data,
                    headers=self._headers,
                )
            except Exception as e:
                logger.error(
                    "Connection error while making %s request to %s: %s",
                    method,
                    endpoint,
                    e,
                )
                return None
        elif method == Methods.POST:
            try:
                response = requests.post(
                    f"{self._base_url}{endpoint}",
                    params=data,
                    headers=self._headers,
                )
            except Exception as e:
                logger.error(
                    "Connection error while making %s request to %s: %s",
                    method,
                    endpoint,
                    e,
                )
                return None
        elif method == Methods.DELETE:
            try:
                response = requests.delete(
                    f"{self._base_url}{endpoint}",
                    params=data,
                    headers=self._headers,
                )
            except Exception as e:
                logger.error(
                    "Connection error while making %s request to %s: %s",
                    method,
                    endpoint,
                    e,
                )
                return None
        else:
            raise ValueError(f"Accepted methods are {Methods.all()}")

        if response.status_code == 200:
            return response.json()
        else:
            logger.error(
                f"Error while making {method} request to {endpoint}: "
                f"{response.json()} (error code {response.status_code})"
            )
            return None

    def get_contracts(self) -> Dict[str, Contract]:
        exchange_info = self._make_request(Methods.GET, BINANCE_CONTRACTS_URL, None)

        contracts = dict()
        if exchange_info is not None:
            for contract_data in exchange_info["symbols"]:
                contracts[contract_data["symbol"]] = Contract(contract_data, Exchange.binance)

        return contracts

    def get_historical_candles(self, contract: Contract, interval: str) -> List[Candle]:
        data = {"symbol": contract.symbol, "interval": interval, "limit": 1000}

        raw_candles = self._make_request(Methods.GET, BINANCE_HISTORIC_CANDLES_URL, data)

        candles = []
        if raw_candles is not None:
            for c in raw_candles:
                candles.append(Candle(c, interval, Exchange.binance))

        return candles

    def get_bid_ask(self, contract: Contract) -> Dict[str, float]:
        data = {"symbol": contract.symbol}
        ob_data = self._make_request(Methods.GET, BINANCE_BID_ASK_URL, data)
        if ob_data is not None:
            if contract.symbol not in self.prices:
                self.prices[contract.symbol] = {
                    "bid": float(ob_data["bidPrice"]),
                    "ask": float(ob_data["askPrice"]),
                }
            else:
                self.prices[contract.symbol]["bid"] = float(ob_data["bidPrice"])
                self.prices[contract.symbol]["ask"] = float(ob_data["askPrice"])

            return self.prices[contract.symbol]

    def get_balances(self) -> Dict[str, Balance]:
        data = dict()
        data["timestamp"] = int(time.time() * 1000)
        data["signature"] = self._generate_signature(data)

        balances = dict()
        account_data = self._make_request(Methods.GET, BINANCE_ACCOUNT_URL, data)
        if account_data is not None:
            for a in account_data["assets"]:
                balances[a["asset"]] = Balance(a, Exchange.binance)

        return balances

    def place_order(
        self,
        contract: Contract,
        order_type: str,
        quantity: float,
        side: str,
        price=None,
        time_in_force=None,
    ) -> OrderStatus:
        data = dict()
        data["symbol"] = contract.symbol
        data["side"] = side.upper()
        data["quantity"] = round(round(quantity / contract.lot_size) * contract.lot_size, 8)
        data["type"] = order_type
        if price is not None:
            data["price"] = round(round(price / contract.tick_size) * contract.tick_size, 8)
        if time_in_force is not None:
            data["timeInForce"] = time_in_force
        data["timestamp"] = int(time.time() * 1000)
        data["signature"] = self._generate_signature(data)

        order_status = self._make_request(Methods.POST, BINANCE_ORDER_URL, data)
        if order_status is not None:
            order_status = OrderStatus(order_status, Exchange.binance)

        return order_status

    def cancel_order(self, contract: Contract, order_id: int) -> OrderStatus:
        data = dict()
        data["orderId"] = order_id
        data["symbol"] = contract.symbol
        data["timestamp"] = int(time.time() * 1000)
        data["signature"] = self._generate_signature(data)

        order_status = self._make_request(Methods.DELETE, BINANCE_ORDER_URL, data)
        if order_status is not None:
            order_status = OrderStatus(order_status, Exchange.binance)

        return order_status

    def get_order_status(self, contract: Contract, order_id: str) -> OrderStatus:
        data = dict()
        data["timestamp"] = int(time.time() * 1000)
        data["symbol"] = contract.symbol
        data["order_id"] = order_id
        data["signature"] = self._generate_signature(data)

        order_status = self._make_request(Methods.GET, BINANCE_ORDER_URL, data)
        if order_status is not None:
            order_status = OrderStatus(order_status, Exchange.binance)

        return order_status

    def _start_ws(self):
        self.ws = websocket.WebSocketApp(
            self._wss_url,
            on_open=self._on_open,
            on_close=self._on_close,
            on_error=self._on_error,
            on_message=self._on_message,
        )
        while True:
            try:
                self.ws.run_forever()
            except Exception as e:
                logger.error("Binance error in run_forever() method: %s", e)
            time.sleep(2)

    def _on_open(self, ws):
        logger.info("Binance connection opened")
        self.subscribe_channel(list(self.contracts.values()), "bookTicker")

    def _on_close(self, ws):
        logger.warning("Binance Websocket connection closed")

    def _on_error(self, ws, msg: str):
        logger.error("Binance connection error: %s", msg)

    def _on_message(self, ws, msg: str):
        data = json.loads(msg)
        if "e" in data:
            if data["e"] == "bookTicker":
                symbol = data["s"]
                if symbol not in self.prices:
                    self.prices[symbol] = {
                        "bid": float(data["b"]),
                        "ask": float(data["a"]),
                    }
                else:
                    self.prices[symbol]["bid"] = float(data["b"])
                    self.prices[symbol]["ask"] = float(data["a"])

                # PNL Calculation
                try:
                    for b_index, strategy in self.strategies.items():
                        if strategy.contract.symbol == symbol:
                            for trade in strategy.trades:
                                if trade.status == "open" and trade.entry_price is not None:
                                    if trade.side == "long":
                                        trade.pnl = (self.prices[symbol]["bid"] - trade.entry_price) * trade.quantity
                                    elif trade.side == "short":
                                        trade.pnl = (trade.entry_price - self.prices[symbol]["ask"]) * trade.quantity
                except RuntimeError as e:
                    logger.error("Error while looping through the Binance strategies: %s", e)

            elif data["e"] == "aggTrade":
                symbol = data["s"]
                for key, strategy in self.strategies.items():
                    if strategy.contract.symbol == symbol:
                        res = strategy.parse_trades(float(data["p"]), float(data["q"]), data["T"])
                        strategy.check_trade(res)

    def subscribe_channel(self, contracts: List[Contract], channel: str):
        data = {
            "method": "SUBSCRIBE",
            "params": [f"{contract.symbol.lower()}@{channel}" for contract in contracts],
            "id": self._ws_id,
        }

        try:
            self.ws.send(json.dumps(data))
        except Exception as e:
            logger.error(
                "Connection error while subscribing to %s %s updates: %s",
                len(contracts),
                channel,
                e,
            )
            return None

        self._ws_id += 1

    def get_trade_size(self, contract: Contract, price: float, balance_pct: float):
        balance = self.get_balances()
        if balance is not None:
            if "USDT" in balance:
                balance = balance["USDT"].wallet_balance
            else:
                return None
        else:
            return None

        trade_size = (balance * balance_pct / 100) / price
        trade_size = round(round(trade_size / contract.lot_size) * contract.lot_size, 8)

        logger.info(
            "Binance futures current USDT balance = %s, trade size = %s",
            balance,
            trade_size,
        )

        return trade_size
