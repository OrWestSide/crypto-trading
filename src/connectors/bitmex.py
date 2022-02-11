import hashlib
import hmac
import json
import logging
import threading
import time
from typing import Dict, Optional, List, Union
from urllib.parse import urlencode

import dateutil.parser
import requests
import websocket

from constants import (
    BITMEX_TESTNET_BASE_URL,
    BITMEX_BASE_URL,
    BITMEX_CONTRACTS_URL,
    BITMEX_TESTNET_WS_URL,
    BITMEX_WS_URL,
    BITMEX_BALANCES_URL,
    BITMEX_HISTORIC_CANDLES_URL,
    BITMEX_ORDER_URL,
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


class BitmexClient:
    def __init__(self, public_key: str, private_key: str, testnet: bool):
        if testnet:
            self._base_url = BITMEX_TESTNET_BASE_URL
            self._wss_url = BITMEX_TESTNET_WS_URL
        else:
            self._base_url = BITMEX_BASE_URL
            self._wss_url = BITMEX_WS_URL

        self._public_key = public_key
        self._private_key = private_key

        self._ws = None

        self.contracts = self.get_contracts()
        self.balances = self.get_balances()

        self.prices = dict()
        self.strategies: Dict[int, Union[TechnicalStrategy, BreakoutStrategy]] = dict()

        self.logs = []

        t = threading.Thread(target=self._start_ws)
        t.start()

        logger.info("Bitmex Client successfully initialized")

    def _add_logs(self, msg: str):
        logger.info("%s", msg)
        self.logs.append({"log": msg, "displayed": False})

    def _generate_signature(self, method: Methods, endpoint: str, expires: str, data: Dict) -> str:
        message = (
            f"{method.value}{endpoint}?{urlencode(data)}{expires}"
            if len(data) > 0
            else f"{method.value}{endpoint}{expires}"
        )
        return hmac.new(self._private_key.encode(), message.encode(), hashlib.sha256).hexdigest()

    def _make_request(self, method: Methods, endpoint: str, data: Optional[Dict]):
        headers = dict()

        expires = str(int(time.time()) + 5)
        headers["api-expires"] = expires
        headers["api-key"] = self._public_key
        headers["api-signature"] = self._generate_signature(method, endpoint, expires, data)

        if method == Methods.GET:
            try:
                response = requests.get(f"{self._base_url}{endpoint}", params=data, headers=headers)
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
                response = requests.post(f"{self._base_url}{endpoint}", params=data, headers=headers)
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
                response = requests.delete(f"{self._base_url}{endpoint}", params=data, headers=headers)
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
        instruments = self._make_request(Methods.GET, BITMEX_CONTRACTS_URL, dict())

        contracts = dict()
        if instruments is not None:
            for instrument in instruments:
                contracts[instrument["symbol"]] = Contract(instrument, Exchange.bitmex)

        return contracts

    def get_balances(self) -> Dict[str, Balance]:
        data = dict()
        data["currency"] = "all"

        margin_data = self._make_request(Methods.GET, BITMEX_BALANCES_URL, data)

        balances = dict()
        if margin_data is not None:
            for a in margin_data:
                balances[a["currency"]] = Balance(a, Exchange.bitmex)
        return balances

    def get_historical_candles(self, contract: Contract, timeframe: str) -> List[Candle]:
        data = dict()
        data["symbol"] = contract.symbol
        data["partial"] = True
        data["binSize"] = timeframe
        data["count"] = 500
        data["reverse"] = True

        raw_candles = self._make_request(Methods.GET, BITMEX_HISTORIC_CANDLES_URL, data)

        candles = []
        if raw_candles is not None:
            for c in reversed(raw_candles):
                candles.append(Candle(c, timeframe, Exchange.bitmex))
        return candles

    def place_order(
        self,
        contract: Contract,
        order_type: str,
        quantity: int,
        side: str,
        price=None,
        time_in_force=None,
    ) -> OrderStatus:
        data = dict()

        data["symbol"] = contract.symbol
        data["side"] = side.capitalize()
        data["orderQty"] = round(quantity / contract.lot_size) * contract.lot_size
        data["ordrType"] = order_type.capitalize()
        if price is not None:
            data["price"] = round(round(price / contract.tick_size) * contract.tick_size, 8)
        if time_in_force is not None:
            data["timeInForce"] = time_in_force

        order_status = self._make_request(Methods.POST, BITMEX_ORDER_URL, data)

        if order_status is not None:
            order_status = OrderStatus(order_status, Exchange.bitmex)
        return order_status

    def cancel_order(self, order_id: str) -> OrderStatus:
        data = dict()
        data["orderID"] = order_id

        order_status = self._make_request(Methods.DELETE, BITMEX_ORDER_URL, data)

        if order_status is not None:
            order_status = OrderStatus(order_status[0], Exchange.bitmex)
        return order_status

    def get_order_status(self, contract: Contract, order_id: str) -> OrderStatus:
        data = dict()
        data["symbol"] = contract.symbol
        data["reverse"] = True

        order_status = self._make_request(Methods.GET, BITMEX_ORDER_URL, data)

        if order_status is not None:
            for order in order_status:
                if order["orderID"] == order_id:
                    return OrderStatus(order_status[0], Exchange.bitmex)

    def _start_ws(self):
        self._ws = websocket.WebSocketApp(
            self._wss_url,
            on_open=self._on_open,
            on_close=self._on_close,
            on_error=self._on_error,
            on_message=self._on_message,
        )
        while True:
            try:
                self._ws.run_forever()
            except Exception as e:
                logger.error("Bitmex error in run_forever() method: %s", e)
            time.sleep(2)

    def _on_open(self, ws):
        logger.info("Bitmex connection opened")
        self.subscribe_channel("instrument")
        self.subscribe_channel("trade")

    def _on_close(self, ws):
        logger.warning("Bitmex Websocket connection closed")

    def _on_error(self, ws, msg: str):
        logger.error("Bitmex connection error: %s", msg)

    def _on_message(self, ws, msg: str):
        data = json.loads(msg)
        if "table" in data:
            if data["table"] == "instrument":
                for d in data["data"]:
                    symbol = d["symbol"]
                    if symbol not in self.prices:
                        self.prices[symbol] = {"bid": None, "ask": None}
                    if "bidPrice" in d:
                        self.prices[symbol]["bid"] = float(d["bidPrice"]) if d["bidPrice"] is not None else None
                    if "askPrice" in d:
                        self.prices[symbol]["ask"] = float(d["askPrice"]) if d["askPrice"] is not None else None

                        # PNL Calculation
                        try:
                            for b_index, strategy in self.strategies.items():
                                if strategy.contract.symbol == symbol:
                                    for trade in strategy.trades:
                                        if trade.status == "open" and trade.entry_price is not None:
                                            if trade.side == "long":
                                                price = self.prices[symbol]["bid"]
                                            else:
                                                price = self.prices[symbol]["ask"]
                                            multiplier = trade.contract.multiplier

                                            if trade.contract.inverse:
                                                if trade.side == "long":
                                                    trade.pnl = (
                                                        (1 / trade.entry_price - 1 / price)
                                                        * multiplier
                                                        * trade.quantity
                                                    )
                                                elif trade.side == "short":
                                                    trade.pnl = (
                                                        (1 / price - 1 / trade.entry_price)
                                                        * multiplier
                                                        * trade.quantity
                                                    )
                                            else:
                                                if trade.side == "long":
                                                    trade.pnl = (
                                                        (price - trade.entry_price) * multiplier * trade.quantity
                                                    )
                                                elif trade.side == "short":
                                                    trade.pnl = (
                                                        (trade.entry_price - price) * multiplier * trade.quantity
                                                    )
                        except RuntimeError as e:
                            logger.error("Error while looping through the Bitmex strategies: %s", e)

            if data["table"] == "trade":
                for d in data["data"]:
                    symbol = d["symbol"]
                    ts = int(dateutil.parser.isoparse(d["timestamp"]).timestamp() * 1000)

                    for key, strategy in self.strategies.items():
                        if strategy.contract.symbol == symbol:
                            res = strategy.parse_trades(float(d["price"]), float(d["size"]), ts)
                            strategy.check_trade(res)

    def subscribe_channel(self, topic: str):
        data = {
            "op": "subscribe",
            "args": [topic],
        }

        try:
            self._ws.send(json.dumps(data))
        except Exception as e:
            logger.error(
                "Connection error while subscribing to %s updates: %s",
                topic,
                e,
            )
            return None

    def get_trade_size(self, contract: Contract, price: float, balance_pct: float):
        balance = self.get_balances()
        if balance is not None:
            if "XBt" in balance:
                balance = balance["XBt"].wallet_balance
            else:
                return None
        else:
            return None

        xbt_size = balance * balance_pct / 100

        if contract.inverse:
            contracts_number = xbt_size / (contract.multiplier / price)
        elif contract.quanto:
            contracts_number = xbt_size / (contract.multiplier * price)
        else:
            contracts_number = xbt_size / (contract.multiplier * price)

        logger.info(
            "Bitmex currenct XBt balance = %s, contracts number = %s",
            balance,
            contracts_number,
        )

        return int(contracts_number)
