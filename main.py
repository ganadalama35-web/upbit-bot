import time
import pyupbit
from dotenv import load_dotenv
import os
import requests
import csv
from datetime import datetime

# 환경변수 로드
load_dotenv()

access = os.getenv("UPBIT_ACCESS_KEY")
secret = os.getenv("UPBIT_SECRET_KEY")

telegram_token = os.getenv("TELEGRAM_BOT_TOKEN")
telegram_chat_id = os.getenv("TELEGRAM_CHAT_ID")

print(telegram_token)
print(telegram_chat_id)

upbit = pyupbit.Upbit(access, secret)

tickers = ["KRW-BTC", "KRW-ETH", "KRW-XRP"]

def get_rsi(df, period=14):
    delta = df['close'].diff()

    up = delta.clip(lower=0)
    down = -delta.clip(upper=0)

    gain = up.rolling(period).mean()
    loss = down.rolling(period).mean()

    rs = gain / loss

    rsi = 100 - (100 / (1 + rs))

    return rsi.iloc[-1]

def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{telegram_token}/sendMessage"

    data = {
        "chat_id": telegram_chat_id,
        "text": message
    }

    requests.post(url, data=data)


def save_log(action, price, amount):
    with open("trade_log.csv", "a", newline="", encoding="utf-8-sig") as file:
        writer = csv.writer(file)

        writer.writerow([
            datetime.now(),
            action,
            price,
            amount
        ])

# 설정값
BUY_AMOUNT = 10000
last_buy_times = {}   
BUY_COOLDOWN = 300
is_buying = False
TAKE_PROFIT = 1.03   # +3%
STOP_LOSS = 0.97     # -3%

send_telegram_message("자동매매 봇 시작")
while True:
    try:
        # 현재가
        for ticker in tickers:

            current_price = pyupbit.get_current_price(ticker)

            # OHLCV 데이터
            df = pyupbit.get_ohlcv(ticker, interval="minute5", count=20)

            ma5 = df['close'].rolling(5).mean().iloc[-1]
            ma20 = df['close'].rolling(20).mean().iloc[-1]
            rsi = get_rsi(df)
            volume = df['volume'].iloc[-1]
            avg_volume = df['volume'].rolling(10).mean().iloc[-1]

            # 잔고
            krw = upbit.get_balance("KRW")
            coin = ticker.split("-")[1]

            btc = upbit.get_balance(coin)
            avg_buy_price = upbit.get_avg_buy_price(coin)

            profit_rate = 0

            if avg_buy_price > 0:
                profit_rate = ((current_price - avg_buy_price) / avg_buy_price) * 100

            print("=" * 40)
            print("코인:", ticker)
            print("현재가:", current_price)
            print("5MA:", ma5)
            print("20MA:", ma20)
            print("RSI:", round(rsi, 2))
            print("거래량:", round(volume))
            print("KRW:", krw)
            print("보유수량:", btc)
            print("평균매수가:", avg_buy_price)
            print("수익률:", round(profit_rate, 2), "%")

            # 매수 조건
            current_time = time.time()

            if (
                ma5 > ma20 and rsi < 35 and volume > avg_volume
                and krw > BUY_AMOUNT
                and btc == 0
                and current_time - last_buy_times.get(ticker, 0) > BUY_COOLDOWN
                and not is_buying
            ):
                is_buying = True
                print("매수 실행")
                send_telegram_message(f"매수 완료: {ticker} / 가격: {current_price}")
                upbit.buy_market_order(ticker, BUY_AMOUNT)
                save_log("BUY", current_price, BUY_AMOUNT)
                last_buy_times[ticker] = current_time
                is_buying = False

            # 익절 / 손절
            if (
                btc > 0
                and (
                    current_price >= avg_buy_price * TAKE_PROFIT
                    or rsi > 70
                )
            ):
                if current_price >= avg_buy_price * TAKE_PROFIT:
                    print("익절 매도")
                    send_telegram_message(f"익절 매도 완료 / 가격: {current_price}")
                    upbit.sell_market_order(ticker, btc)

                elif current_price <= avg_buy_price * STOP_LOSS:
                    print("손절 매도")
                    upbit.sell_market_order(ticker, btc)

            time.sleep(10)

    except Exception as e:
            print("에러:", e)
            send_telegram_message(f"에러 발생: {e}")
            time.sleep(10)
        