import logging

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
        self.balance_pct = balance_pct
        self.take_profit = take_profit
        self.stop_loss = stop_loss
