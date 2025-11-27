import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os

# 랜덤 고정
np.random.seed(42)

PRODUCTS = {
    "이온음료": {"base_price": 100.0, "base_sales": 50},
    "오꾸밥": {"base_price": 200.0, "base_sales": 30},
    "아이스크림": {"base_price": 150.0, "base_sales": 25},
    "젤리": {"base_price": 80.0, "base_sales": 40},
    "포켓몬빵": {"base_price": 120.0, "base_sales": 35},
}

DAYS = 30

# --- 하루하루 이벤트 설정 (팝업 + 설명용) ---
EVENTS = {
    1:  {"code": "모의고사",  "title": "모의고사", 
         "desc": "전학년 모의고사 날입니다. 학생들이 긴장해서 간단한 음료 위주로 소비할 수 있어요."},
    2:  {"code": "중간고사1", "title": "중간고사 1일차 (생윤·수1·생1)",
         "desc": "생윤, 수학1, 생명1 시험일입니다. 점심시간이 빠듯해서 식사는 줄고 간단 간식/음료 소비가 늘 수 있어요."},
    3:  {"code": "중간고사2", "title": "중간고사 2일차 (독서)",
         "desc": "독서 시험일입니다. 비교적 여유가 있어 가벼운 간식 소비가 조금 늘 수 있어요."},
    4:  {"code": "중간고사3", "title": "중간고사 3일차 (일본어·영어)",
         "desc": "일본어, 영어 시험일입니다. 외국어 시험 스트레스로 달달한 간식 소비가 증가할 수 있습니다."},
    5:  {"code": "중간고사4", "title": "중간고사 4일차 (확통·기가)",
         "desc": "중간고사의 마지막 날이라 분위기가 조금 풀리며 소비가 회복될 수 있어요."},
    6:  {"code": "체험학습", "title": "체험학습",
         "desc": "1,2학년은 체험학습을 나가고, 3학년만 오전수업을 합니다. 학교에 학생이 적어 매점 매출이 크게 줄어요."},
    7:  {"code": "오전수업", "title": "오전수업만 하는 날",
         "desc": "오전수업만 하는 날이라 점심 이후에는 학생이 거의 없습니다. 점심 전 소비만 발생합니다."},
    8:  {"code": "단축수업", "title": "단축수업",
         "desc": "수업 시간이 줄어 점심시간이 짧거나 변동이 있어, 식사 계열(오꾸밥)은 줄고 간식/음료가 약간 늘 수 있어요."},
    9:  {"code": "이동수업", "title": "이동수업 많은 날",
         "desc": "각 반이 이리저리 이동수업을 많이 하는 날입니다. 이동 중 간식/음료 소비가 늘 수 있습니다."},
    10: {"code": "이동수업", "title": "이동수업 많은 날",
         "desc": "이동수업으로 복도/운동장 이동이 잦아, 시원한 음료와 간단 간식 수요가 증가합니다."},
    11: {"code": "이동수업", "title": "이동수업 많은 날",
         "desc": "체육, 실험 등으로 이동이 많아 땀을 흘려 이온음료와 아이스크림 수요가 늘어요."},
    12: {"code": "이동수업", "title": "이동수업 많은 날",
         "desc": "교실 이동이 잦은 날입니다. 포켓몬빵 같은 휴대 간식도 인기가 있을 수 있어요."},
    13: {"code": "이동수업", "title": "이동수업 많은 날",
         "desc": "이동수업 마지막 날. 피로 누적으로 달달한 간식 수요도 증가할 수 있어요."},
    14: {"code": "수행많음", "title": "수행평가가 많은 날",
         "desc": "수행평가가 많아 늦게까지 남아서 과제를 준비하는 날입니다. 음료와 간식 소비가 늘어납니다."},
    15: {"code": "수행많음", "title": "수행평가가 많은 날",
         "desc": "조별과제, 발표 준비 등으로 친구들과 함께 매점에서 간단히 먹을 일이 많습니다."},
    16: {"code": "수행많음", "title": "수행평가가 많은 날",
         "desc": "수행평가 준비로 피로가 누적되어 고칼로리 간식 선호도가 높아질 수 있어요."},
    17: {"code": "수행많음", "title": "수행평가가 많은 날",
         "desc": "방과 후까지 남아 있는 학생이 많아, 오후 시간대 소비도 발생합니다."},
    18: {"code": "수행많음", "title": "수행평가가 많은 날",
         "desc": "수행의 막바지라 긴장감이 커져, 달달한 간식과 음료 소비가 많이 일어납니다."},
    19: {"code": "축제", "title": "학교 축제",
         "desc": "오전: 학교 부스 체험 / 오후: 학교 밖 축제. 오전에 잠깐 매점 이용, 오후에는 학교에 학생이 거의 없습니다."},
}

# 나머지 20~30일은 일반일
for d in range(20, DAYS + 1):
    EVENTS[d] = {
        "code": "일반일",
        "title": "일반적인 수업일",
        "desc": "특별한 행사가 없는 평범한 수업일입니다. 온도와 습도에 따라 아이스크림·이온음료 수요가 달라질 수 있어요."
    }


def run_simulation(schedule_override=None, seed=42):
    np.random.seed(seed)
    records = []
    prev_prices = {p: PRODUCTS[p]["base_price"] for p in PRODUCTS}

    for day in range(1, DAYS + 1):
        temp = int(np.random.choice(range(10, 36)))
        humidity = int(np.random.choice(range(20, 91)))

        event_info = EVENTS.get(day, {"code": "일반일"})
        event_code = event_info["code"]

        if schedule_override and day in schedule_override:
            event_code = schedule_override[day]

        for p in PRODUCTS:
            base = PRODUCTS[p]["base_sales"]
            modifier = 0.0

            # 이벤트 효과 (조금 단순화)
            if event_code == "모의고사":
                if p == "이온음료":
                    modifier += 0.3
                elif p == "오꾸밥":
                    modifier -= 0.4
                else:
                    modifier -= 0.2
            elif event_code.startswith("중간고사"):
                if p == "이온음료":
                    modifier += 0.2
                elif p == "오꾸밥":
                    modifier -= 0.3
                else:
                    modifier -= 0.25
            elif event_code == "체험학습":
                modifier -= 0.6
            elif event_code == "오전수업":
                modifier -= 0.5
            elif event_code == "단축수업":
                if p == "오꾸밥":
                    modifier -= 0.4
                else:
                    modifier -= 0.2
            elif event_code == "이동수업":
                if p == "이온음료":
                    modifier += 0.1
                elif p == "포켓몬빵":
                    modifier += 0.15
                elif p == "오꾸밥":
                    modifier -= 0.1
            elif event_code == "수행많음":
                if p == "이온음료":
                    modifier += 0.25
                elif p == "젤리":
                    modifier += 0.2
                elif p == "포켓몬빵":
                    modifier += 0.15
                elif p == "오꾸밥":
                    modifier += 0.1
                elif p == "아이스크림":
                    modifier -= 0.1
            elif event_code == "축제":
                modifier -= 0.5

            # 일반일에서의 온도 효과
            if event_code == "일반일":
                if temp >= 28:
                    if p in ("이온음료", "아이스크림"):
                        modifier += 0.3
                elif temp <= 15:
                    if p == "아이스크림":
                        modifier -= 0.5
                    if p == "오꾸밥":
                        modifier += 0.05

            noise = np.random.uniform(-0.1, 0.1)
            units = max(0, int(round(base * (1 + modifier + noise))))
            revenue = units * prev_prices[p]

            sales_change_pct = (units - base) / base if base > 0 else 0
            price_change_pct = 0.4 * sales_change_pct + np.random.uniform(-0.03, 0.03)
            price_end = prev_prices[p] * (1 + price_change_pct)

            records.append({
                "day": day,
                "date": (datetime.today() + timedelta(days=day - 1)).strftime("%Y-%m-%d"),
                "event": event_code,
                "temp": temp,
                "humidity": humidity,
                "product": p,
                "price_start": prev_prices[p],
                "price_end": price_end,
                "units_sold": units,
                "revenue": revenue,
            })

            prev_prices[p] = price_end

    df = pd.DataFrame(records)
    os.makedirs("data", exist_ok=True)
    csv_path = os.path.join("data", "maejeom_simulation_30days.csv")
    df.to_csv(csv_path, index=False, encoding="utf-8-sig")

    return df, csv_path
