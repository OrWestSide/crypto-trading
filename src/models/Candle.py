import datetime
from typing import Union

import dateutil.parser

from helpers.Exchange import Exchange

BITMEX_TF_MINUTES = {"1m": 5, "5m": 5, "1h": 60, "1d": 1440}


class Candle:
    def __init__(self, candle_info, timeframe, exchange: Union[Exchange, str]):
        if exchange == Exchange.binance:
            self.timestamp = candle_info[0]
            self.open = float(candle_info[1])
            self.high = float(candle_info[2])
            self.low = float(candle_info[3])
            self.close = float(candle_info[4])
            self.volume = float(candle_info[5])
        elif exchange == Exchange.bitmex:
            self.timestamp = dateutil.parser.isoparse(candle_info["timestamp"])
            self.timestamp = self.timestamp - datetime.timedelta(minutes=BITMEX_TF_MINUTES[timeframe])
            self.timestamp = int(self.timestamp.timestamp() * 1000)
            self.open = candle_info["open"]
            self.high = candle_info["high"]
            self.low = candle_info["low"]
            self.close = candle_info["close"]
            self.volume = candle_info["volume"]
        elif exchange == "past_trade":
            self.timestamp = candle_info["ts"]
            self.open = candle_info["open"]
            self.high = candle_info["high"]
            self.low = candle_info["low"]
            self.close = candle_info["close"]
            self.volume = candle_info["volume"]
