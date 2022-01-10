import logging
import tkinter as tk
from connectors.binance_futures import BinanceFuturesClient
from connectors.bitmex import BitmexClient
from constants import (BINANCE_TESTNET_API_KEY, BINANCE_TESTNET_API_SECRET, BITMEX_TESTNET_API_SECRET,
                       BITMEX_TESTNET_API_KEY)
from ui.root_component import Root

logger = logging.getLogger()

logger.setLevel(logging.DEBUG)

stream_handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s %(levelname)s :: %(message)s')
stream_handler.setFormatter(formatter)
stream_handler.setLevel(logging.INFO)

file_handler = logging.FileHandler('info.log')
file_handler.setFormatter(formatter)
file_handler.setLevel(logging.DEBUG)

logger.addHandler(stream_handler)
logger.addHandler(file_handler)

if __name__ == '__main__':
    binance = BinanceFuturesClient(public_key=BINANCE_TESTNET_API_KEY,
                                   private_key=BINANCE_TESTNET_API_SECRET,
                                   testnet=True)
    bitmex = BitmexClient(public_key=BITMEX_TESTNET_API_KEY,
                          private_key=BITMEX_TESTNET_API_SECRET,
                          testnet=True)

    root = Root(binance, bitmex)
    root.mainloop()
