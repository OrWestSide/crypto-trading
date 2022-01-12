from helpers.Exchange import Exchange


class OrderStatus:
    def __init__(self, order_info, exchange: Exchange):
        if exchange == Exchange.binance:
            self.order_id = order_info["orderId"]
            self.status = order_info["status"]
            self.avg_price = order_info["avgPrice"]
        elif exchange == Exchange.bitmex:
            self.order_id = order_info["orderID"]
            self.status = order_info["ordStatus"]
            self.avg_price = order_info["avgPx"]
