import os
from dotenv import load_dotenv
from openai import OpenAI
from pybithumb import Bithumb
import json
import openai

client = OpenAI()

# .env 가져오기
load_dotenv()

# 1. 차트 데이터 가져오기
df = Bithumb.get_candlestick("BTC", chart_intervals="24h")
df_tail = df.tail(30)  # 30일 기준
json_data = df_tail.to_json(orient="records")  # JSON

# 2. chatgpt에 물어보기
openai.api_key = os.getenv("OPENAI_API_KEY")  # open ai API

response = openai.ChatCompletion.create(
    model="gpt-4",  # 모델 설정
    messages=[  # 질문하기
        {
            "role": "system",
            "content": (
                "You're a Bitcoin investment expert with a 1-minute time frame. Based on the provided chart data, tell me whether I should buy, sell, or hold. Respond in JSON format.\n\n Response Example:\n"
                "{\"decision\": \"buy\", \"reason\": \"some technical reason\"}\n"
                "{\"decision\": \"sell\", \"reason\": \"some technical reason\"}\n"
                "{\"decision\": \"hold\", \"reason\": \"some technical reason\"}"
            )
        },
        {
            "role": "user",
            "content": json_data  # AI에게 차트 데이터 전달
        }
    ]
)

# 응답 체크 (NoneType 오류 방지) (?)
if response.choices:
    result = response.choices[0].message["content"]  # OpenAI 응답에서 콘텐츠 추출
    print("AI Response:", result)
else:
    print("Error: No choices in the response.")

# 3. 거래 진
result = json.loads(result)  # JSON 데이터로 변환

# Bithumb API 키 설정
seckey = os.getenv("BITHUMB_SECRET_KEY")  # Bithumb API 키 (SECRET_KEY)
conkey = os.getenv("BITHUMB_ACCESS_KEY")  # Bithumb API 키 (ACCESS_KEY)

bithumb = Bithumb(conkey, seckey)

coin = "BTC"  # 거래할 코인
current_price = Bithumb.get_current_price(coin)  # 현재 BTC 가격

if result["decision"] == "buy":
    # 매수: 현재 잔고(원화)로 가능한 최대 수량 매수
    krw_balance = bithumb.get_balance("KRW")[0]  # 잔고 조회
    available_krw = krw_balance / (1 + 0.004)  # 수수료를 고려한 실제 사용 가능 금액; 수수료 할인 쿠폰 생기면 수정해야됨..!
    if available_krw >= 5000:  # 최소 매수 금액 확인
        quantity_to_buy = available_krw / current_price  # 매수 가능한 BTC 수량 계산
        print(f"매수 결정: {quantity_to_buy:.8f} BTC")
        print(bithumb.buy_market_order(coin, quantity_to_buy))  # 시장가 매수
    else:
        print("매수할 수 있는 최소 금액(5,000원)이 부족합니다.")
        
elif result["decision"] == "sell":
    # 매도: 보유한 코인의 전체 수량 매도
    coin_balance = bithumb.get_balance(coin)[0]  # 보유한 코인 잔고 조회
    coin_value = coin_balance * current_price  # 보유 코인의 원화 가치 계산
    if coin_value >= 5000:  # 보유 코인의 원화 가치가 최소 금액 이상인지 확인
        print(f"매도 결정: {coin_balance:.8f} BTC")
        print(bithumb.sell_market_order(coin, coin_balance))  # 시장가 매도
    else:
        print("보유한 BTC의 원화 가치가 부족하여 매도할 수 없습니다.")
        
elif result["decision"] == "hold":
    # 대기 상태일 때 이유 출력
    print(f"보류 결정: {result['reason']}")
    print("AI가 현재 시장 상황에서 대기 상태를 추천했습니다. 아무 작업도 수행하지 않습니다.")
