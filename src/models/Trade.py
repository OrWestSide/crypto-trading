from models.Contract import Contract


class Trade:
    def __init__(self, trade_info):
        self.time: int = trade_info["time"]
        self.contract: Contract = trade_info["contract"]
        self.strategy: str = trade_info["strategy"]
        self.side: str = trade_info["side"]
        self.entry_price: float = trade_info["entry_price"]
        self.status: str = trade_info["status"]
        self.pnl: float = trade_info["pnl"]
        self.quantity = trade_info["quantity"]
        self.entry_id = trade_info["entry_id"]
