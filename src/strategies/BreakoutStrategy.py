from typing import Dict

from models.Contract import Contract
from strategies.Strategy import Strategy


class BreakoutStrategy(Strategy):
    def __init__(self,
                 contract: Contract,
                 exchange: str,
                 timeframe: str,
                 balance_pct: float,
                 take_profit: float,
                 stop_loss: float,
                 other_params: Dict):
        super().__init__(contract, exchange, timeframe, balance_pct, take_profit, stop_loss)

        self._min_volume = other_params["min_volume"]
