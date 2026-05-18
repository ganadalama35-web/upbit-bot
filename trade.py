import pyupbit

def buy_coin(upbit, ticker, money):
    upbit.buy_market_order(ticker, money)

def sell_coin(upbit, ticker):
    balance = upbit.get_balance("BTC")

    if balance > 0:
        upbit.sell_market_order(ticker, balance)