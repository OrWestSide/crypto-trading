import logging
from typing import List

from constants import TF_EQUIV
from models.Candle import Candle
from models.Contract import Contract

logger = logging.getLogger()


class Strategy:
    def __init__(self,
                 contract: Contract,
                 exchange: str,
                 timeframe: str,
                 balance_pct: float,
                 take_profit: float,
                 stop_loss: float):
        self.contract = contract
        self.exchange = exchange
        self.timeframe = timeframe
        self.tf_equiv = TF_EQUIV[timeframe] * 1000
        self.balance_pct = balance_pct
        self.take_profit = take_profit
        self.stop_loss = stop_loss

        self.candles: List[Candle] = []

    def parse_trades(self, price: float, size: float, timestamp: int) -> str:
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
            missing_candles = int((timestamp - last_candle.timestamp) / self.tf_equiv) - 1
            logger.info(f"{self.exchange} missing {missing_candles} candles for "
                        f"{self.contract.symbol} {self.timeframe} "
                        f"({timestamp} {last_candle.timestamp})")

            for missing in range(missing_candles):
                new_ts = last_candle.timestamp + self.tf_equiv
                candle_info = {
                    "ts": new_ts,
                    "open": last_candle.close,
                    "high": last_candle.close,
                    "low": last_candle.close,
                    "close": last_candle.close,
                    "volume": 0
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
                "volume": size
            }
            new_candle = Candle(candle_info, self.timeframe, "parse_trade")
            self.candles.append(new_candle)

            logger.info(f"{self.exchange} New candle for {self.contract.symbol} {self.timeframe}")

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
                "volume": size
            }
            new_candle = Candle(candle_info, self.timeframe, "parse_trade")
            self.candles.append(new_candle)

            logger.info(f"{self.exchange} New candle for {self.contract.symbol} {self.timeframe}")

            return "new_candle"
