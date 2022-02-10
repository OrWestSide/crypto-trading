from typing import Dict, Tuple

import pandas as pd

from helpers.Strategies import Strategies
from models.Contract import Contract
from strategies.Strategy import Strategy


class TechnicalStrategy(Strategy):
    def __init__(
        self,
        client,
        contract: Contract,
        exchange: str,
        timeframe: str,
        balance_pct: float,
        take_profit: float,
        stop_loss: float,
        other_params: Dict,
    ):
        super().__init__(
            client,
            contract,
            exchange,
            timeframe,
            balance_pct,
            take_profit,
            stop_loss,
            Strategies.technical,
        )

        self._ema_fast = other_params["ema_fast"]
        self._ema_slow = other_params["ema_slow"]
        self._ema_signal = other_params["ema_signal"]

        self._rsi_length = other_params["rsi_length"]

    def _rsi(self):
        close_list = [candle.close for candle in self.candles]
        closes = pd.Series(close_list)

        delta = closes.diff().dropna()

        up, down = delta.copy(), delta.copy()
        up[up < 0] = 0
        down[down > 0] = 0

        avg_gain = up.ewm(
            com=(self._rsi_length - 1), min_periods=self._rsi_length
        ).mean()
        avg_loss = (
            down.abs()
            .ewm(com=(self._rsi_length - 1), min_periods=self._rsi_length)
            .mean()
        )

        rs = avg_gain / avg_loss
        rsi = 100 - 100 / (1 + rs)
        rsi = rsi.round(2)

        return rsi.iloc[-2]

    def _macd(self) -> Tuple[float, float]:
        close_list = [candle.close for candle in self.candles]
        closes = pd.Series(close_list)

        ema_fast = closes.ewm(span=self._ema_fast).mean()
        ema_slow = closes.ewm(span=self._ema_slow).mean()

        macd_line = ema_fast - ema_slow
        macd_signal = macd_line.ewm(span=self._ema_signal).mean()

        return macd_line.iloc[-2], macd_signal.iloc[-2]

    def _check_signal(self):
        macd_line, macd_signal = self._macd()
        rsi = self._rsi()

        if rsi < 30 and macd_line > macd_signal:
            return 1
        elif rsi > 70 and macd_line < macd_signal:
            return -1
        else:
            return 0

    def check_trade(self, tick_type: str):
        if tick_type == "new_candle" and not self.open_position:
            signal_result = self._check_signal()
            if signal_result in [-1, 1]:
                self._open_position(signal_result)
