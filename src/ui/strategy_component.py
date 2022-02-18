import json
import tkinter as tk
from tkinter import ttk

from connectors.binance_futures import BinanceFuturesClient
from connectors.bitmex import BitmexClient
from database.database import WorkspaceData
from helpers.Exchange import Exchange
from helpers.Strategies import Strategies
from helpers.validators import check_integer_format, check_float_format
from strategies.BreakoutStrategy import BreakoutStrategy
from strategies.TechnicalStrategy import TechnicalStrategy
from ui.scrollable_frame import ScrollableFrame
from ui.styling import (
    BG_COLOR,
    GLOBAL_FONT,
    BG_COLOR_2,
    FG_COLOR,
    BOLD_FONT,
    BUTTON_DELETE_COLOR,
    BUTTON_GREEN,
)


class StrategyEditor(tk.Frame):
    def __init__(
        self,
        root,
        binance: BinanceFuturesClient,
        bitmex: BitmexClient,
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)

        self.db = WorkspaceData()

        self.root = root

        self._valid_integer = self.register(check_integer_format)
        self._valid_float = self.register(check_float_format)

        self._exchanges = {"Binance": binance, "Bitmex": bitmex}

        self._all_contracts = []
        self._all_timeframes = ["1m", "5m", "15m", "30m", "1h", "4h"]

        for exchange, client in self._exchanges.items():
            for symbol, contract in client.contracts.items():
                self._all_contracts.append(f"{symbol}_{exchange.capitalize()}")

        self._commands_frame = tk.Frame(self, bg=BG_COLOR)
        self._commands_frame.pack(side=tk.TOP)

        self._table_frame = tk.Frame(self, bg=BG_COLOR)
        self._table_frame.pack(side=tk.TOP)

        self._add_button = tk.Button(
            self._commands_frame,
            text="Add strategy",
            font=GLOBAL_FONT,
            command=self._add_strategy_row,
            bg=BG_COLOR_2,
            fg=FG_COLOR,
        )
        self._add_button.pack(side=tk.TOP)

        self.body_widgets = dict()

        self._headers_frame = tk.Frame(self._table_frame, bg=BG_COLOR)

        self.additional_parameters = dict()
        self._extra_input = dict()

        self._base_params = [
            {
                "code_name": "strategy_type",
                "widget": tk.OptionMenu,
                "data_type": str,
                "values": Strategies.values(),
                "width": 10,
                "header": "Strategy",
            },
            {
                "code_name": "contract",
                "widget": ttk.Combobox,
                "data_type": str,
                "values": self._all_contracts,
                "width": 15,
                "header": "Contract",
            },
            {
                "code_name": "timeframe",
                "widget": tk.OptionMenu,
                "data_type": str,
                "values": self._all_timeframes,
                "width": 10,
                "header": "Timeframe",
            },
            {"code_name": "balance_pct", "widget": tk.Entry, "data_type": float, "width": 10, "header": "Balance %"},
            {"code_name": "take_profit", "widget": tk.Entry, "data_type": float, "width": 7, "header": "TP %"},
            {"code_name": "stop_loss", "widget": tk.Entry, "data_type": float, "width": 7, "header": "SL %"},
            {
                "code_name": "parameters",
                "widget": tk.Button,
                "data_type": float,
                "text": "Parameters",
                "bg": BG_COLOR_2,
                "command": self._show_popup,
                "header": "",
                "width": 8,
            },
            {
                "code_name": "activation",
                "widget": tk.Button,
                "data_type": float,
                "text": "OFF",
                "bg": BUTTON_DELETE_COLOR,
                "command": self._switch_strategy,
                "header": "",
                "width": 6,
            },
            {
                "code_name": "delete",
                "widget": tk.Button,
                "data_type": float,
                "text": "X",
                "bg": BUTTON_DELETE_COLOR,
                "command": self._delete_row,
                "header": "",
                "width": 4,
            },
        ]

        self.extra_params = {
            Strategies.technical.value: [
                {
                    "code_name": "rsi_length",
                    "name": "RSI Periods",
                    "widget": tk.Entry,
                    "data_type": int,
                },
                {
                    "code_name": "ema_fast",
                    "name": "MACD Fast Length",
                    "widget": tk.Entry,
                    "data_type": int,
                },
                {
                    "code_name": "ema_slow",
                    "name": "MACD Slow Length",
                    "widget": tk.Entry,
                    "data_type": int,
                },
                {
                    "code_name": "ema_signal",
                    "name": "MACD Signal Length",
                    "widget": tk.Entry,
                    "data_type": int,
                },
            ],
            Strategies.breakout.value: [
                {
                    "code_name": "min_volume",
                    "name": "Minimum volume",
                    "widget": tk.Entry,
                    "data_type": float,
                }
            ],
        }

        for idx, h in enumerate(self._base_params):
            header = tk.Label(
                self._headers_frame,
                text=h["header"],
                bg=BG_COLOR,
                fg=FG_COLOR,
                font=GLOBAL_FONT,
                width=h["width"],
                bd=1,
                relief=tk.FLAT,
            )
            header.grid(row=0, column=idx, padx=2)
        header = tk.Label(
            self._headers_frame, text="", bg=BG_COLOR, fg=FG_COLOR, font=GLOBAL_FONT, width=8, bd=1, relief=tk.FLAT
        )
        header.grid(row=0, column=len(self._base_params), padx=2)

        self._headers_frame.pack(side=tk.TOP, anchor="nw")

        self._body_frame = ScrollableFrame(self._table_frame, bg=BG_COLOR, height=250)
        self._body_frame.pack(side=tk.TOP, fill=tk.X, anchor="nw")

        for h in self._base_params:
            self.body_widgets[h["code_name"]] = dict()
            if h["widget"] == tk.OptionMenu or h["widget"] == ttk.Combobox:
                self.body_widgets[h["code_name"] + "_var"] = dict()

        self._body_index = 0

        self._load_workspace()

    def _add_strategy_row(self):
        b_index = self._body_index

        for col, base_params in enumerate(self._base_params):
            code_name = base_params["code_name"]
            if base_params["widget"] == tk.OptionMenu:
                self.body_widgets[code_name + "_var"][b_index] = tk.StringVar()
                self.body_widgets[code_name + "_var"][b_index].set(base_params["values"][0])
                self.body_widgets[code_name][b_index] = tk.OptionMenu(
                    self._body_frame.sub_frame,
                    self.body_widgets[code_name + "_var"][b_index],
                    *base_params["values"],
                )
                self.body_widgets[code_name][b_index].config(
                    width=base_params["width"], bd=0, indicatoron=0, font=GLOBAL_FONT, highlightthickness=False
                )
            elif base_params["widget"] == tk.Entry:
                self.body_widgets[code_name][b_index] = tk.Entry(
                    self._body_frame.sub_frame,
                    justify=tk.CENTER,
                    font=GLOBAL_FONT,
                    bd=1,
                    highlightthickness=False,
                    width=base_params["width"],
                )

                if base_params["data_type"] == int:
                    self.body_widgets[code_name][b_index].config(
                        validate="key", validatecommand=(self._valid_integer, "%P")
                    )
                if base_params["data_type"] == float:
                    self.body_widgets[code_name][b_index].config(
                        validate="key", validatecommand=(self._valid_float, "%P")
                    )
            elif base_params["widget"] == tk.Button:
                self.body_widgets[code_name][b_index] = tk.Button(
                    self._body_frame.sub_frame,
                    text=base_params["text"],
                    bg=base_params["bg"],
                    fg=FG_COLOR,
                    font=GLOBAL_FONT,
                    width=base_params["width"],
                    command=lambda frozen_command=base_params["command"]: frozen_command(b_index),
                )
            elif base_params["widget"] == ttk.Combobox:
                self.body_widgets[code_name + "_var"][b_index] = tk.StringVar()
                self.body_widgets[code_name + "_var"][b_index].set(base_params["values"][0])
                self.body_widgets[code_name][b_index] = ttk.Combobox(
                    self._body_frame.sub_frame,
                    textvariable=self.body_widgets[code_name + "_var"][b_index],
                    values=base_params["values"],
                )
                self.body_widgets[code_name][b_index].config(width=base_params["width"], font=GLOBAL_FONT)
            else:
                continue

            self.body_widgets[code_name][b_index].grid(row=b_index, column=col, padx=2)

        self.additional_parameters[b_index] = dict()

        for strategy, params in self.extra_params.items():
            for param in params:
                self.additional_parameters[b_index][param["code_name"]] = None

        self._body_index += 1

    def _show_popup(self, b_index: int):
        x = self.body_widgets["parameters"][b_index].winfo_rootx()
        y = self.body_widgets["parameters"][b_index].winfo_rooty()

        self._popup_window = tk.Toplevel(self)
        self._popup_window.wm_title("Parameters")
        self._popup_window.config(bg=BG_COLOR)
        self._popup_window.attributes("-topmost", "true")
        self._popup_window.grab_set()

        self._popup_window.geometry(f"+{x - 80}+{y + 30}")

        strategy_selected = self.body_widgets["strategy_type_var"][b_index].get()

        row_nb = 0
        for param in self.extra_params[strategy_selected]:
            code_name = param["code_name"]
            temp_label = tk.Label(
                self._popup_window,
                bg=BG_COLOR,
                fg=FG_COLOR,
                text=param["name"],
                font=BOLD_FONT,
            )
            temp_label.grid(row=row_nb, column=0)

            if param["widget"] == tk.Entry:
                self._extra_input[code_name] = tk.Entry(
                    self._popup_window,
                    bg=BG_COLOR_2,
                    justify=tk.CENTER,
                    fg=FG_COLOR,
                    insertbackground=FG_COLOR,
                )

                if param["data_type"] == int:
                    self._extra_input[code_name].config(validate="key", validatecommand=(self._valid_integer, "%P"))
                if param["data_type"] == float:
                    self._extra_input[code_name].config(validate="key", validatecommand=(self._valid_float, "%P"))

                if self.additional_parameters[b_index][code_name] is not None:
                    self._extra_input[code_name].insert(
                        tk.END,
                        str(self.additional_parameters[b_index][code_name]),
                    )
            else:
                continue
            self._extra_input[code_name].grid(row=row_nb, column=1)

            row_nb += 1

        validation_button = tk.Button(
            self._popup_window,
            text="Validate",
            bg=BG_COLOR_2,
            fg=FG_COLOR,
            command=lambda: self._validate_parameters(b_index),
        )
        validation_button.grid(row=row_nb, column=0, columnspan=2)

    def _validate_parameters(self, b_index: int):
        strategy_selected = self.body_widgets["strategy_type_var"][b_index].get()
        for param in self.extra_params[strategy_selected]:
            code_name = param["code_name"]
            if self._extra_input[code_name].get() == "":
                self.additional_parameters[b_index][code_name] = None
            else:
                self.additional_parameters[b_index][code_name] = param["data_type"](self._extra_input[code_name].get())

        self._popup_window.destroy()

    def _switch_strategy(self, b_index: int):
        for param in ["balance_pct", "take_profit", "stop_loss"]:
            if self.body_widgets[param][b_index].get() == "":
                self.root.logging_frame.add_log(f"Missing {param} parameter")
                return

        strategy_selected = self.body_widgets["strategy_type_var"][b_index].get()
        for param in self.extra_params[strategy_selected]:
            if self.additional_parameters[b_index][param["code_name"]] is None:
                self.root.logging_frame.add_log(f"Missing {param['code_name']} parameter")
                return

        symbol = self.body_widgets["contract_var"][b_index].get().split("_")[0]
        timeframe = self.body_widgets["timeframe_var"][b_index].get()
        exchange = self.body_widgets["contract_var"][b_index].get().split("_")[1]

        contract = self._exchanges[exchange].contracts[symbol]

        balance_pct = float(self.body_widgets["balance_pct"][b_index].get())
        take_profit = float(self.body_widgets["take_profit"][b_index].get())
        stop_loss = float(self.body_widgets["stop_loss"][b_index].get())

        if self.body_widgets["activation"][b_index].cget("text") == "OFF":
            if strategy_selected == Strategies.technical.value:
                new_strategy = TechnicalStrategy(
                    client=self._exchanges[exchange],
                    contract=contract,
                    exchange=exchange,
                    timeframe=timeframe,
                    balance_pct=balance_pct,
                    take_profit=take_profit,
                    stop_loss=stop_loss,
                    other_params=self.additional_parameters[b_index],
                )
            elif strategy_selected == Strategies.breakout.value:
                new_strategy = BreakoutStrategy(
                    client=self._exchanges[exchange],
                    contract=contract,
                    exchange=exchange,
                    timeframe=timeframe,
                    balance_pct=balance_pct,
                    take_profit=take_profit,
                    stop_loss=stop_loss,
                    other_params=self.additional_parameters[b_index],
                )
            else:
                return

            new_strategy.candles = self._exchanges[exchange].get_historical_candles(contract, timeframe)
            if len(new_strategy.candles) == 0:
                self.root.logging_frame.add_log(f"No historical data retrieved for {contract.symbol}")
                return
            if exchange == Exchange.binance.value:
                self._exchanges[exchange].subscribe_channel([contract], "aggTrade")

            self._exchanges[exchange].strategies[b_index] = new_strategy

            for param in self._base_params:
                code_name = param["code_name"]
                if code_name != "activation" and "_var" not in code_name:
                    self.body_widgets[code_name][b_index].config(state=tk.DISABLED)
            self.body_widgets["activation"][b_index].config(bg=BUTTON_GREEN, text="ON")
            self.root.logging_frame.add_log(f"{strategy_selected} strategy on {symbol} / " f"{timeframe} started")
        else:
            del self._exchanges[exchange].strategies[b_index]

            for param in self._base_params:
                code_name = param["code_name"]
                if code_name != "activation" and "_var" not in code_name:
                    self.body_widgets[code_name][b_index].config(state=tk.NORMAL)
            self.body_widgets["activation"][b_index].config(bg=BUTTON_DELETE_COLOR, text="OFF")
            self.root.logging_frame.add_log(f"{strategy_selected} strategy on {symbol} / " f"{timeframe} stopped")

    def _delete_row(self, b_index: int):
        for element in self._base_params:
            self.body_widgets[element["code_name"]][b_index].grid_forget()
            del self.body_widgets[element["code_name"]][b_index]

    def _load_workspace(self):
        data = self.db.get("strategies")

        for row in data:
            self._add_strategy_row()

            b_index = self._body_index - 1

            for base_params in self._base_params:
                code_name = base_params["code_name"]

                if base_params["widget"] == tk.OptionMenu or base_params["widget"] == ttk.Combobox:
                    if row[code_name] is not None:
                        self.body_widgets[code_name + "_var"][b_index].set(row[code_name])
                elif base_params["widget"] == tk.Entry:
                    if row[code_name] is not None:
                        self.body_widgets[code_name][b_index].insert(tk.END, row[code_name])

            extra_params = json.loads(row["extra_params"])
            for param, value in extra_params.items():
                if value is not None:
                    self.additional_parameters[b_index][param] = value
