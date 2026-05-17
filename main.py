import pyupbit
import time
import datetime
from dotenv import dotenv_values

# API 키 읽기
config = dotenv_values(".env")

ACCESS_KEY = config.get("UPBIT_ACCESS_KEY")
SECRET_KEY = config.get("UPBIT_SECRET_KEY")

# 업비트 연결
upbit = pyupbit.Upbit(ACCESS_KEY, SECRET_KEY)

# 목표가 계산
def get_target_price(ticker, k):
    df = pyupbit.get_ohlcv(ticker, interval="day", count=2)

    if df is None:
        return None

    target = df.iloc[0]['close'] + (
        df.iloc[0]['high'] - df.iloc[0]['low']
    ) * k

    return float(target)

# 현재가 조회
def get_current_price(ticker):
    price = pyupbit.get_current_price(ticker)

    if price is None:
        return None

    return float(price)

print("자동매매 시작")

ticker = "KRW-BTC"
k = 0.5

while True:
    try:
        now = datetime.datetime.now()

        target_price = get_target_price(ticker, k)
        current_price = get_current_price(ticker)

        # 가격 조회 실패 방지
        if target_price is None or current_price is None:
            print("가격 조회 실패")
            time.sleep(5)
            continue

        # 잔고 조회
        krw = float(upbit.get_balance("KRW") or 0)
        btc = float(upbit.get_balance("BTC") or 0)

        print("---------------")
        print("시간:", now)
        print("현재가:", current_price)
        print("목표가:", target_price)
        print("KRW:", krw)
        print("BTC:", btc)

        # 매수 조건
        if current_price > target_price:
            if krw >= 5000:
                if btc < 0.00001:

                    print("매수 실행")

                    result = upbit.buy_market_order(
                        ticker,
                        5000
                    )

                    print(result)

        # 매도 조건
        if btc > 0.00001:

            if now.hour == 8 and now.minute == 59:

                print("매도 실행")

                result = upbit.sell_market_order(
                    ticker,
                    btc
                )

                print(result)

        time.sleep(5)

    except Exception as e:
        print("오류:", e)
        time.sleep(5)