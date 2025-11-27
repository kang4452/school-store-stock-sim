import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os

# 랜덤 고정 (결과 재현 가능)
np.random.seed(42)

# 제품 기본 설정
PRODUCTS = {
    "이온음료": {"base_price": 100.0, "base_sales": 50},
    "오꾸밥": {"base_price": 200.0, "base_sales": 30},
    "아이스크림": {"base_price": 150.0, "base_sales": 25},
    "젤리": {"base_price": 80.0, "base_sales": 40},
    "포켓몬빵": {"base_price": 120.0, "base_sales": 35},
}

DAYS = 30

def run_simulation(schedule_override=None, seed=42):
    """
    기본 30일 매점 매출/가격 시뮬레이터
    - schedule_override : {1:"모의고사", 2:"체험학습"} 같은 형태 (지금은 안 써도 됨)
    - 반환값 : (DataFrame, CSV 저장 경로)
    """
    np.random.seed(seed)

    records = []

    # 첫날 기준 가격 설정
    prev_prices = {p: PRODUCTS[p]["base_price"] for p in PRODUCTS}

    for day in range(1, DAYS + 1):

        # 온도 / 습도는 임의값
        temp = int(np.random.choice(range(10, 36)))
        humidity = int(np.random.choice(range(20, 91)))

        # 이벤트 (기본은 일반일)
        event = "일반일"
        if schedule_override and day in schedule_override:
            event = schedule_override[day]

        # 모든 제품 시뮬레이션
        for p in PRODUCTS:

            # 기본 판매량 + 랜덤 노이즈
            base = PRODUCTS[p]["base_sales"]
            noise = np.random.uniform(-0.1, 0.1)  # -10% ~ +10%
            units = max(0, int(round(base * (1 + noise))))

            # 매출 = 판매량 × 가격
            revenue = units * prev_prices[p]

            # 가격 하루 변동 (랜덤 ±5%)
            price_end = prev_prices[p] * (1 + np.random.uniform(-0.05, 0.05))

            # 데이터 기록
            records.append({
                "day": day,
                "date": (datetime.today() + timedelta(days=day - 1)).strftime("%Y-%m-%d"),
                "event": event,
                "temp": temp,
                "humidity": humidity,
                "product": p,
                "price_start": prev_prices[p],
                "price_end": price_end,
                "units_sold": units,
                "revenue": revenue,
            })

            # 다음 날을 위한 가격 업데이트
            prev_prices[p] = price_end

    # DataFrame으로 변환
    df = pd.DataFrame(records)

    # CSV 파일 저장
    csv_path = os.path.join("data", "maejeom_simulation_30days.csv")
    df.to_csv(csv_path, index=False, encoding="utf-8-sig")

    return df, csv_path
