import logging
import time
from threading import Timer
from typing import List, TYPE_CHECKING, Union

from constants import TF_EQUIV
from helpers.Strategies import Strategies
from models.Candle import Candle
from models.Contract import Contract
from models.Trade import Trade

if TYPE_CHECKING:
    from connectors.bitmex import BitmexClient
    from connectors.binance_futures import BinanceFuturesClient

logger = logging.getLogger()


class Strategy:
    def __init__(
        self,
        client: Union["BitmexClient", "BinanceFuturesClient"],
        contract: Contract,
        exchange: str,
        timeframe: str,
        balance_pct: float,
        take_profit: float,
        stop_loss: float,
        strategy_name: Strategies,
    ):
        self.client = client
        self.contract = contract
        self.exchange = exchange
        self.timeframe = timeframe
        self.tf_equiv = TF_EQUIV[timeframe] * 1000
        self.balance_pct = balance_pct
        self.take_profit = take_profit
        self.stop_loss = stop_loss

        self.strategy_name = strategy_name

        self.open_position = False

        self.candles: List[Candle] = []
        self.trades: List[Trade] = []
        self.logs = []

    def _add_log(self, msg: str):
        logger.info("%s", msg)
        self.logs.append({"log": msg, "displayed": False})

    def parse_trades(self, price: float, size: float, timestamp: int) -> str:
        timestamp_diff = int(time.time() * 1000) - timestamp
        if timestamp_diff >= 2000:
            logger.warning(
                "%s %s: %s milliseconds of difference between the current"
                " time and the trade time",
                self.exchange,
                self.contract.symbol,
                timestamp_diff,
            )

        last_candle = self.candles[-1]

        # Same candle
        if timestamp < last_candle.timestamp + self.tf_equiv:
            last_candle.close = price
            last_candle.volume += size

            if price > last_candle.high:
                last_candle.high = price
            elif price < last_candle.low:
                last_candle.low = price

            return "same_candle"

        # Missing candles
        elif timestamp >= last_candle.timestamp + 2 * self.tf_equiv:
            missing_candles = (
                int((timestamp - last_candle.timestamp) / self.tf_equiv) - 1
            )
            logger.info(
                f"{self.exchange} missing {missing_candles} candles for "
                f"{self.contract.symbol} {self.timeframe} "
                f"({timestamp} {last_candle.timestamp})"
            )

            for missing in range(missing_candles):
                new_ts = last_candle.timestamp + self.tf_equiv
                candle_info = {
                    "ts": new_ts,
                    "open": last_candle.close,
                    "high": last_candle.close,
                    "low": last_candle.close,
                    "close": last_candle.close,
                    "volume": 0,
                }
                new_candle = Candle(candle_info, self.timeframe, "parse_trade")
                self.candles.append(new_candle)

                last_candle = new_candle

            new_ts = last_candle.timestamp + self.tf_equiv
            candle_info = {
                "ts": new_ts,
                "open": price,
                "high": price,
                "low": price,
                "close": price,
                "volume": size,
            }
            new_candle = Candle(candle_info, self.timeframe, "parse_trade")
            self.candles.append(new_candle)

            logger.info(
                f"{self.exchange} New candle for {self.contract.symbol}"
                f" {self.timeframe}"
            )

            return "new_candle"

        # New candle
        elif timestamp >= last_candle.timestamp + self.tf_equiv:
            new_ts = last_candle.timestamp + self.tf_equiv
            candle_info = {
                "ts": new_ts,
                "open": price,
                "high": price,
                "low": price,
                "close": price,
                "volume": size,
            }
            new_candle = Candle(candle_info, self.timeframe, "parse_trade")
            self.candles.append(new_candle)

            logger.info(
                f"{self.exchange} New candle for {self.contract.symbol} "
                f"{self.timeframe}"
            )

            return "new_candle"

    def _open_position(self, signal_result: int):
        trade_size = self.client.get_trade_size(
            self.contract, self.candles[-1].close, self.balance_pct
        )
        if trade_size is None:
            return

        order_side = "buy" if signal_result == 1 else "sell"
        position_side = "long" if signal_result == 1 else "short"

        self._add_log(
            f"{position_side.capitalize()} signal on"
            f" {self.contract.symbol} {self.timeframe}"
        )

        order_status = self.client.place_order(
            self.contract, "MARKET", trade_size, order_side
        )
        if order_status is not None:
            self._add_log(
                f"{order_side.capitalize()} order placed on {self.exchange}"
                f" | Status: {order_status.status}"
            )
            self.ongoing_position = True

            avg_fill_price = None
            if order_status.status == "filled":
                avg_fill_price = order_status.avg_price
            else:
                t = Timer(
                    2.0,
                    lambda: self._check_order_status(order_status.order_id),
                )
                t.start()

            new_trade = Trade(
                {
                    "time": int(time.time() * 1000),
                    "entry_price": avg_fill_price,
                    "contract": self.contract,
                    "strategy": self.strategy_name,
                    "side": position_side,
                    "status": "open",
                    "pnl": 0,
                    "quantity": trade_size,
                    "entry_id": order_status.order_id,
                }
            )
            self.trades.append(new_trade)

    def _check_order_status(self, order_id):
        order_status = self.client.get_order_status(self.contract, order_id)
        if order_status is not None:
            logger.info(
                "%s order status: %s", self.exchange, order_status.status
            )

            if order_status.status == "filled":
                for trade in self.trades:
                    if trade.entry_id == order_id:
                        trade.entry_price = order_status.avg_price
                        break
                return

        t = Timer(2.0, lambda: self._check_order_status(order_id))
        t.start()
