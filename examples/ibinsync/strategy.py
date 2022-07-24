from big_algo_framework.strategies.abstract_strategy import *
from big_algo_framework.brokers.ib import IB
from big_algo_framework.data.td import TDData
from big_algo_framework.big.options import filter_option_contract
from big_algo_framework.big.position_sizing import PositionSizing
from datetime import datetime, timedelta

broker = None

class IBORB(Strategy):
    def __init__(self, order_dict):
        super().__init__()
        self.is_position = True
        self.is_order = True
        self.orders_list = []
        self.pos_list = []

        self.ip_address = order_dict["ip_address"]
        self.port = order_dict["port"]
        self.ib_client = order_dict["ib_client"]
        self.order_id = order_dict["order_id"]
        self.ticker = order_dict["ticker"]
        self.primary_exchange = order_dict["primary_exchange"]
        self.time_frame = order_dict["time_frame"]
        self.entry_time = order_dict["entry_time"]
        self.entry = order_dict["entry"]
        self.sl = order_dict["sl"]
        self.tp1 = order_dict["tp1"]
        self.tp2 = order_dict["tp2"]
        self.risk = order_dict["risk"]
        self.direction = order_dict["direction"]
        self.is_close = order_dict["is_close"]
        self.mkt_close_time = order_dict["mkt_close_time"]
        self.sec_type = order_dict["sec_type"]
        self.option_action = order_dict["option_action"]
        self.option_range = order_dict["option_range"]
        self.option_strikes = order_dict["option_strikes"]
        self.option_expiry_days = order_dict["option_expiry_days"]
        self.currency = order_dict["currency"]
        self.exchange = order_dict["exchange"]
        self.lastTradeDateOrContractMonth = order_dict["lastTradeDateOrContractMonth"]
        self.strike = order_dict["strike"]
        self.right = order_dict["right"]
        self.multiplier = order_dict["multiplier"]
        self.ask_price = order_dict["ask_price"]
        self.account_no = order_dict["account_no"]
        self.funds = order_dict["funds"]
        self.total_risk = order_dict["total_risk"]
        self.total_risk_units = order_dict["total_risk_units"]
        self.max_position_percent = order_dict["max_position_percent"]
        self.tda_api = order_dict["tda_api"]

    async def connect_broker(self):
        global broker
        if(broker == None) or (not broker.isConnected()):
            broker = IB()
            await broker.connectAsync(self.ip_address, self.port, self.ib_client)
        self.broker = broker
        self.account_dict = await self.broker.get_account()

    async def check_open_orders(self):
        self.orders_list = self.broker.get_order_by_ticker(self.ticker)

        if len(self.orders_list) == 0:
            self.is_order = False

    async def check_positions(self):
        self.pos_list = await self.broker.get_position_by_ticker(self.ticker)

        if len(self.pos_list) == 0:
            self.is_position = False

    async def before_send_orders(self):
        self.gtd = datetime.fromtimestamp(self.mkt_close_time / 1000)

        # FILTER OPTIONS
        data = TDData(api_key=self.tda_api)
        contract_type = ""

        if (self.direction == "Bullish" and self.option_action == "BUY") or \
                (self.direction == "Bearish" and self.option_action == "SELL"):
            contract_type = "CALL"

        elif (self.direction == "Bullish" and self.option_action == "SELL") or \
                (self.direction == "Bearish" and self.option_action == "BUY"):
            contract_type = "PUT"

        options_df = await data.get_historic_option_data(symbol=self.ticker,
                                           contract_type=contract_type,
                                           range=self.option_range,
                                           days_forward=10,
                                           )

        option_contract = filter_option_contract(direction=self.direction,
                                                   open_action=self.option_action,
                                                   option_range=self.option_range,
                                                   option_strikes=self.option_strikes,
                                                   stock_price=self.entry,
                                                   option_expiry_days=self.option_expiry_days,
                                                   options_df=options_df)

        self.lastTradeDateOrContractMonth = option_contract["lastTradeDateOrContractMonth"]
        self.strike = option_contract["strike"]
        self.right = option_contract["right"]
        self.ask = option_contract["ask"]
        self.bid = option_contract["bid"]
        self.symbol = option_contract["symbol"]
        self.multiplier = option_contract["multiplier"]

        # ACTION
        self.open_action = self.option_action
        self.close_action = "SELL" if self.open_action == "BUY" else "BUY"

        self.stock_entry = self.entry
        self.stock_sl = self.sl

        self.entry = self.ask
        self.sl = 0

        # Position Sizing
        self.risk_unit = abs(self.entry - self.sl)
        position = PositionSizing(self.account_dict["AvailableFunds"],
                                  self.total_risk,
                                  self.total_risk_units,
                                  self.risk_unit,
                                  self.max_position_percent,
                                  self.entry)
        self.quantity = position.options_quantity(self.multiplier)

        # Contract
        self.stock_contract = await self.broker.get_stock_contract(self.ticker, self.exchange, self.currency, self.primary_exchange)
        self.option_contract = await self.broker.get_options_contract(
                                                                      self.ticker,
                                                                      self.lastTradeDateOrContractMonth,
                                                                      self.strike,
                                                                      self.right,
                                                                      self.exchange,
                                                                      self.multiplier,
                                                                      self.currency)

        # Prepare Orders
        self.x = True if self.direction == "Bullish" else False
        self.y = False if self.direction == "Bullish" else True

    async def send_orders(self):
        # # TRAILING STOP
        # entry_order = await self.broker.get_trailing_stop_limit_order(action=self.open_action,
        #                                                  quantity=self.quantity,
        #                                                 trail_type="PERCENTAGE",
        #                                                 trail_amount=2,
        #                                                   trail_stop=0.25,
        #                                                 trail_limit=0.5,
        #                                                 #   limit_price_offset=0,
        #                                                  duration="GTD",
        #                                                  good_till_date=(self.gtd + timedelta(minutes=-30)).strftime('%Y%m%d %H:%M:%S'),
        #                                                  account_no=self.account_no,
        #                                                  transmit=False,
        #                                                   sec_type="",
        #                                                   symbol="")
        # entry_trade = await self.broker.send_order(self.option_contract[0], entry_order)

        # OCO ORDERS
        # order_1 = await self.broker.get_stop_order(action=self.open_action, stop_price=2, quantity=self.quantity, transmit=True, sec_type="", symbol="")
        # order_2 = await self.broker.get_market_order(action=self.open_action, quantity=self.quantity, transmit=True, sec_type="", symbol="")
        # orders = [order_1, order_2]
        # entry_order = await self.broker.get_oco_order(orders, "test_group", "CANCEL")
        # for i in range(0, len(orders)):
        #     await self.broker.send_order(self.option_contract[0], entry_order[i])

        # # OTO ORDERS
        # order_1 = await self.broker.get_market_order(action=self.open_action, quantity=self.quantity, transmit=False, sec_type="", symbol="")
        # entry_trade = await self.broker.send_order(self.option_contract[0], order_1)
        #
        # order_2 = await self.broker.get_stop_order(action=self.close_action, quantity=self.quantity, stop_price=1, transmit=False, sec_type="", symbol="")
        # order_3 = await self.broker.get_limit_order(action=self.close_action, quantity=self.quantity, limit_price=5.00, transmit=True, sec_type="", symbol="")

        # orders = [order_2, order_3]
        # entry_order = await self.broker.get_oto_order(entry_trade, orders)
        # for i in range(0, len(orders)):
        #     await self.broker.send_order(self.option_contract[0], entry_order[i])

        # 3 ORDERS (OTO, OCO --- ENTRY/SL/TP)
        entry_order = await self.broker.get_market_order(action=self.open_action,
                                                         quantity=self.quantity,
                                                         duration="GTD",
                                                         good_till_date=(self.gtd + timedelta(minutes=-30)).strftime('%Y%m%d %H:%M:%S'),
                                                         account_no=self.account_no,
                                                         transmit=False,
                                                         sec_type="",
                                                         symbol="")
        p_cond = await self.broker.get_price_condition(
                                                 conjunction='o',
                                                 is_more=self.y,
                                                 price=self.stock_entry,
                                                 contract_id=self.stock_contract[0].conId,
                                                 exchange="SMART",
                                                 trigger_method="DEFAULT")
        entry_order.conditions = [p_cond]
        entry_trade = await self.broker.send_order(self.option_contract[0], entry_order)

        sl_order = await self.broker.get_market_order(action=self.close_action,
                                                      quantity=self.quantity,
                                                      parent_id=entry_trade.order.orderId,
                                                      account_no=self.account_no,
                                                      transmit=False,
                                                      sec_type="",
                                                      symbol="")
        p_cond = await self.broker.get_price_condition(
                                                 conjunction='o',
                                                 is_more=self.y,
                                                 price=self.stock_sl,
                                                 contract_id=self.stock_contract[0].conId,
                                                 exchange="SMART",
                                                trigger_method="DEFAULT")
        sl_order.conditions = [p_cond]
        await self.broker.send_order(self.option_contract[0], sl_order)

        tp_order = await self.broker.get_market_order(action=self.close_action,
                                                      quantity=self.quantity,
                                                      parent_id=entry_trade.order.orderId,
                                                      account_no=self.account_no,
                                                      transmit=True,
                                                      sec_type="",
                                                      symbol="")
        p_cond = await self.broker.get_price_condition(
                                                 conjunction='o',
                                                 is_more=self.x,
                                                 price=self.tp1,
                                                 contract_id=self.stock_contract[0].conId,
                                                 exchange="SMART",
                                                 trigger_method="DEFAULT")
        t_cond = await self.broker.get_time_condition(
                                                conjunction='o',
                                                is_more=True,
                                                time=(self.gtd + timedelta(minutes=-5)).strftime('%Y%m%d %H:%M:%S'))
        tp_order.conditions = [p_cond, t_cond]
        await self.broker.send_order(self.option_contract[0], tp_order)

    async def start(self):
        await self.connect_broker()

    async def execute(self):
        await self.start()

        if self.is_close == 0:
            await self.check_positions()
            if not self.is_position:
                await self.check_open_orders()
                if not self.is_order:
                    await self.before_send_orders()

                    if self.quantity > 0:
                        await self.send_orders()
                        self.after_send_orders()


    # TRADE CLASS OUTPUT!!!!
    # Trade(
    # contract=Stock(conId=270639, symbol='INTC', exchange='SMART', primaryExchange='NASDAQ', currency='USD', localSymbol='INTC', tradingClass='NMS'),
    # order=LimitOrder(orderId=104, clientId=1, permId=1405222075, action='SELL', totalQuantity=1.0, lmtPrice=1.11, auxPrice=0.0),
    # orderStatus=OrderStatus(orderId=104, status='PreSubmitted', filled=0.0, remaining=1.0, avgFillPrice=0.0, permId=1405222075, parentId=0, lastFillPrice=0.0, clientId=1, whyHeld='', mktCapPrice=0.0),
    # fills=[],
    # log=[TradeLogEntry(time=datetime.datetime(2022, 6, 18, 23, 7, 29, 87606, tzinfo=datetime.timezone.utc), status='PendingSubmit', message='', errorCode=0),
    # TradeLogEntry(time=datetime.datetime(2022, 6, 18, 23, 7, 29, 120600, tzinfo=datetime.timezone.utc), status='PreSubmitted', message='', errorCode=0)]),


    # POSITIONS OUTPUT
    # [Position(account='U3584554',
    #           contract=Stock(conId=344439802, symbol='TME', exchange='NYSE', currency='USD', localSymbol='TME', tradingClass='TME'),
    #           position=1.0, avgCost=5.2227)]