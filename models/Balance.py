from helpers.Exchange import Exchange


BITMEX_MULTIPLIER = 0.00000001


class Balance:
    def __init__(self, info, exchange: Exchange):
        if exchange == Exchange.binance:
            self.initial_margin = float(info["initialMargin"])
            self.maintenance_margin = float(info["maintMargin"])
            self.margin_balance = float(info["marginBalance"])
            self.wallet_balance = float(info["walletBalance"])
            self.unrealized_pnl = float(info["unrealizedProfit"])
        elif exchange == Exchange.bitmex:
            self.initial_margin = info["initMargin"] * BITMEX_MULTIPLIER
            self.maintenance_margin = info["maintMargin"] * BITMEX_MULTIPLIER
            self.margin_balance = info["marginBalance"] * BITMEX_MULTIPLIER
            self.wallet_balance = info["walletBalance"] * BITMEX_MULTIPLIER
            self.unrealized_pnl = info["unrealisedPnl"] * BITMEX_MULTIPLIER
