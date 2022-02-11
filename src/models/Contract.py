from typing import Dict

from helpers.Exchange import Exchange
from models.Balance import BITMEX_MULTIPLIER


def tick_to_decimals(tick_size: float) -> int:
    tick_size_str = "{0:.8f}".format(tick_size)
    while tick_size_str[-1] == 0:
        tick_size_str = tick_size_str[:-1]

    split_tick = tick_size_str.split(".")

    if len(split_tick) > 1:
        return len(split_tick[1])
    else:
        return 0


class Contract:
    def __init__(self, contract_info: Dict, exchange: Exchange):
        if exchange == Exchange.binance:
            self.symbol = contract_info["symbol"]
            self.base_asset = contract_info["baseAsset"]
            self.quote_asset = contract_info["quoteAsset"]
            self.price_decimals = contract_info["pricePrecision"]
            self.quantity_decimals = contract_info["quantityPrecision"]
            self.tick_size = 1 / pow(10, contract_info["pricePrecision"])
            self.lot_size = 1 / pow(10, contract_info["quantityPrecision"])
        elif exchange == Exchange.bitmex:
            self.symbol = contract_info["symbol"]
            self.base_asset = contract_info["rootSymbol"]
            self.quote_asset = contract_info["quoteCurrency"]
            self.tick_size = contract_info["tickSize"]
            self.lot_size = contract_info["lotSize"]
            self.price_decimals = tick_to_decimals(self.tick_size)
            self.quantity_decimals = tick_to_decimals(self.lot_size)

            self.quanto = contract_info["isQuanto"]
            self.inverse = contract_info["isInverse"]

            self.multiplier = contract_info["multiplier"] * BITMEX_MULTIPLIER
            if self.inverse:
                self.multiplier *= -1

        self.exchange = exchange
