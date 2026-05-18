import pyupbit
import time
import datetime
import traceback
import csv
import requests

from dotenv import dotenv_values

# =========================
# 환경변수 불러오기
# =========================

config = dotenv_values(".env")

ACCESS_KEY = config.get("UPBIT_ACCESS_KEY")
SECRET_KEY = config.get("UPBIT_SECRET_KEY")

TELEGRAM_TOKEN = config.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = config.get("TELEGRAM_CHAT_ID")

# =========================
# 업비트 연결
# =========================

upbit = pyupbit.Upbit(
    ACCESS_KEY,
    SECRET_KEY
)

# =========================
# 텔레그램 메시지
# =========================

def send_telegram_message(message):

    try:

        url = (
            f"https://api.telegram.org/bot"
            f"{TELEGRAM_TOKEN}/sendMessage"
        )

        data = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message
        }

        requests.post(
            url,
            data=data,
            timeout=10
        )

    except Exception:

        traceback.print_exc()

# =========================
# 목표가 계산
# =========================

def get_target_price(ticker, k):

    df = pyupbit.get_ohlcv(
        ticker,
        interval="day",
        count=2
    )

    if df is None:
        return None

    target = (
        df.iloc[0]['close']
        + (
            df.iloc[0]['high']
            - df.iloc[0]['low']
        ) * k
    )

    return float(target)

# =========================
# 현재가 조회
# =========================

def get_current_price(ticker):

    price = pyupbit.get_current_price(
        ticker
    )

    if price is None:
        return None

    return float(price)

# =========================
# 5일 이동평균
# =========================

def get_ma5(ticker):

    df = pyupbit.get_ohlcv(
        ticker,
        interval="day",
        count=5
    )

    if df is None:
        return None

    ma5 = (
        df['close']
        .rolling(5)
        .mean()
        .iloc[-1]
    )

    return float(ma5)

# =========================
# 로그 저장
# =========================

def save_log(
    now,
    action,
    price,
    krw,
    btc
):

    with open(
        "trade_log.csv",
        "a",
        newline="",
        encoding="utf-8"
    ) as f:

        writer = csv.writer(f)

        writer.writerow([
            now,
            action,
            price,
            krw,
            btc
        ])

# =========================
# 시작
# =========================

print("자동매매 시작")

send_telegram_message(
    "자동매매 시작"
)

ticker = "KRW-BTC"

k = 0.5

last_buy_time = None

while True:

    try:

        now = datetime.datetime.now()

        # =========================
        # 가격 조회
        # =========================

        target_price = get_target_price(
            ticker,
            k
        )

        current_price = get_current_price(
            ticker
        )

        ma5 = get_ma5(ticker)

        # =========================
        # 조회 실패 방지
        # =========================

        if (
            target_price is None
            or current_price is None
            or ma5 is None
        ):

            print("가격 조회 실패")

            time.sleep(5)

            continue

        # =========================
        # 잔고 조회
        # =========================

        krw = float(
            upbit.get_balance("KRW") or 0
        )

        btc = float(
            upbit.get_balance("BTC") or 0
        )

        avg_buy_price = float(
            upbit.get_avg_buy_price(
                ticker
            ) or 0
        )

        # =========================
        # 출력
        # =========================

        print("---------------")

        print("시간:", now)

        print(
            "현재가:",
            current_price
        )

        print(
            "목표가:",
            target_price
        )

        print(
            "5일 이동평균:",
            ma5
        )

        print(
            "KRW:",
            krw
        )

        print(
            "BTC:",
            btc
        )

        print(
            "평균매수가:",
            avg_buy_price
        )

        # =========================
        # 수익률 계산
        # =========================

        if (
            btc > 0.00001
            and avg_buy_price > 0
        ):

            profit_rate = (
                (
                    current_price
                    - avg_buy_price
                )
                / avg_buy_price
            ) * 100

            print(
                "수익률:",
                round(
                    profit_rate,
                    2
                ),
                "%"
            )

        else:

            profit_rate = 0

        # =========================
        # 매수 조건
        # =========================

        can_buy = True

        # 10분 쿨타임
        if last_buy_time:

            diff = (
                now
                - last_buy_time
            ).seconds

            if diff < 600:

                can_buy = False

        if (
            current_price > target_price
            and current_price > ma5
        ):

            if krw >= 5000:

                if btc < 0.00001:

                    if can_buy:

                        print("매수 실행")

                        result = (
                            upbit.buy_market_order(
                                ticker,
                                5000
                            )
                        )

                        print(result)

                        send_telegram_message(
                            f"[매수]\\n"
                            f"현재가: "
                            f"{current_price}"
                        )

                        save_log(
                            now,
                            "매수",
                            current_price,
                            krw,
                            btc
                        )

                        last_buy_time = now

        # =========================
        # 손절
        # =========================

        if btc > 0.00001:

            if profit_rate <= -2:

                print("손절 실행")

                result = (
                    upbit.sell_market_order(
                        ticker,
                        btc
                    )
                )

                print(result)

                send_telegram_message(
                    f"[손절]\\n"
                    f"수익률: "
                    f"{round(profit_rate, 2)}%"
                )

                save_log(
                    now,
                    "손절",
                    current_price,
                    krw,
                    btc
                )

        # =========================
        # 익절
        # =========================

        if btc > 0.00001:

            if profit_rate >= 3:

                print("익절 실행")

                result = (
                    upbit.sell_market_order(
                        ticker,
                        btc
                    )
                )

                print(result)

                send_telegram_message(
                    f"[익절]\\n"
                    f"수익률: "
                    f"{round(profit_rate, 2)}%"
                )

                save_log(
                    now,
                    "익절",
                    current_price,
                    krw,
                    btc
                )

        # =========================
        # 오전 8:59 강제 매도
        # =========================

        if btc > 0.00001:

            if (
                now.hour == 8
                and now.minute == 59
            ):

                print("일일 종료 매도")

                result = (
                    upbit.sell_market_order(
                        ticker,
                        btc
                    )
                )

                print(result)

                send_telegram_message(
                    "[매도]\\n"
                    "일일 종료"
                )

                save_log(
                    now,
                    "매도",
                    current_price,
                    krw,
                    btc
                )

        # =========================
        # API 과호출 방지
        # =========================

        time.sleep(5)

    except Exception:

        traceback.print_exc()

        send_telegram_message(
            "[오류 발생]\\n"
            "프로그램 확인 필요"
        )

        time.sleep(5)