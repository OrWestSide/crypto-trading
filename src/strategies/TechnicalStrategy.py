from typing import Dict

from models.Contract import Contract
from strategies.Strategy import Strategy


class TechnicalStrategy(Strategy):
    def __init__(self,
                 contract: Contract,
                 exchange: str,
                 timeframe: str,
                 balance_pct: float,
                 take_profit: float,
                 stop_loss: float,
                 other_params: Dict):
        super().__init__(contract, exchange, timeframe, balance_pct, take_profit, stop_loss)

        self._ema_fast = other_params["ema_fast"]
        self._ema_slow = other_params["ema_slow"]
        self._ema_signal = other_params["ema_signal"]
