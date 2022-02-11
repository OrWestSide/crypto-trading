import logging
import tkinter as tk

from connectors.binance_futures import BinanceFuturesClient
from connectors.bitmex import BitmexClient
from helpers.Exchange import Exchange
from ui.logging_component import Logging
from ui.strategy_component import StrategyEditor
from ui.styling import BG_COLOR
from ui.trades_component import TradesWatch
from ui.watchlist_component import Watchlist


logger = logging.getLogger()


class Root(tk.Tk):
    def __init__(self, binance: BinanceFuturesClient, bitmex: BitmexClient):
        super().__init__()

        self.binance = binance
        self.bitmex = bitmex

        self.title("Trading Bot")

        self.configure(bg=BG_COLOR)

        self._left_frame = tk.Frame(self, bg=BG_COLOR)
        self._left_frame.pack(side=tk.LEFT)
        self._right_frame = tk.Frame(self, bg=BG_COLOR)
        self._right_frame.pack(side=tk.LEFT)

        self._watchlist_frame = Watchlist(
            self.binance.contracts,
            self.bitmex.contracts,
            self._left_frame,
            bg=BG_COLOR,
        )
        self._watchlist_frame.pack(side=tk.TOP)

        self.logging_frame = Logging(self._left_frame, bg=BG_COLOR)
        self.logging_frame.pack(side=tk.TOP)

        self._strategy_frame = StrategyEditor(self, self.binance, self.bitmex, self._right_frame, bg=BG_COLOR)
        self._strategy_frame.pack(side=tk.TOP)

        self._trades_frame = TradesWatch(self._right_frame, bg=BG_COLOR)
        self._trades_frame.pack(side=tk.TOP)

        self._update_ui()

    def _update_ui(self):
        # Logs
        for log in self.bitmex.logs:
            if not log["displayed"]:
                self.logging_frame.add_log(log["log"])
                log["displayed"] = True
        for log in self.binance.logs:
            if not log["displayed"]:
                self.logging_frame.add_log(log["log"])
                log["displayed"] = True

        # Trades and logs
        for client in [self.binance, self.bitmex]:
            try:
                for b_index, strategy in client.strategies.items():
                    for log in strategy.logs:
                        if not log["displayed"]:
                            self.logging_frame.add_log(log["log"])
                            log["displayed"] = True

                    for trade in strategy.trades:
                        if trade.time not in self._trades_frame.body_widgets["symbol"]:
                            self._trades_frame.add_trade(trade)

                        if trade.contract.exchange == Exchange.binance:
                            precision = trade.contract.price_decimals
                        else:
                            precision = 8

                        pnl_str = "{0:.{prec}f}".format(trade.pnl, prec=precision)
                        self._trades_frame.body_widgets["pnl_var"][trade.time].set(pnl_str)
                        self._trades_frame.body_widgets["status_var"][trade.time].set(trade.status.capitalize())

            except RuntimeError as e:
                logger.error("Error while looping through watchlist dictionary: %s", e)

        # Watchlist
        try:
            for k, v in self._watchlist_frame.body_widgets["symbol"].items():
                symbol = self._watchlist_frame.body_widgets["symbol"][k].cget("text")
                exchange = self._watchlist_frame.body_widgets["exchange"][k].cget("text")

                if exchange == "Binance":
                    if symbol not in self.binance.contracts:
                        continue
                    if symbol not in self.binance.prices:
                        self.binance.get_bid_ask(self.binance.contracts[symbol])
                        continue

                    precision = self.binance.contracts["symbol"].price_decimals

                    prices = self.binance.prices[symbol]
                elif exchange == "Bitmex":
                    if symbol not in self.bitmex.contracts:
                        continue
                    if symbol not in self.bitmex.prices:
                        self.binance.get_bid_ask(self.binance.contracts[symbol])
                        continue

                    precision = self.bitmex.contracts["symbol"].price_decimals

                    prices = self.bitmex.prices[symbol]
                else:
                    continue

                if prices["bid"] is not None:
                    price_str = "{0:.{prec}f}".format(prices["bid"], prec=precision)
                    self._watchlist_frame.body_widgets["bid_var"][k].set(price_str)
                if prices["ask"] is not None:
                    price_str = "{0:.{prec}f}".format(prices["ask"], prec=precision)
                    self._watchlist_frame.body_widgets["ask_var"][k].set(price_str)
        except RuntimeError as e:
            logger.error("Error while looping through the watchlist dictionary: %s", e)

        self.after(1500, self._update_ui)
