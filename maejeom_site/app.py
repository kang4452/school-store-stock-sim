from flask import Flask, render_template, request, jsonify, send_file
from simulation.simulator import run_simulation, PRODUCTS, DAYS
import os
import pandas as pd
import json

app = Flask(__name__, instance_relative_config=True)

DATA_DIR = "data"
STATE_FILE = os.path.join(DATA_DIR, "game_state.json")
PRICES_FILE = os.path.join(DATA_DIR, "prices.csv")


# ---------- 유틸 함수들 ----------

def ensure_data_dir():
    os.makedirs(DATA_DIR, exist_ok=True)


def init_simulation():
    """30일 가격 시뮬레이션을 새로 돌리고, 게임 상태도 초기화"""
    ensure_data_dir()
    df, csv_path = run_simulation()
    # 가격 정보만 따로 저장 (편하게 쓰기 위해)
    df.to_csv(PRICES_FILE, index=False, encoding="utf-8-sig")

    # 초기 게임 상태
    state = {
        "day": 1,
        "cash": 1_000_000,  # 시작 현금 (원하는 대로 바꿔도 됨)
        "holdings": {p: 0 for p in PRODUCTS.keys()},
        "history": []  # 주문 내역
    }
    save_state(state)
    return df, state


def load_prices_df():
    ensure_data_dir()
    if not os.path.exists(PRICES_FILE):
        df, _ = init_simulation()
        return df
    return pd.read_csv(PRICES_FILE, encoding="utf-8-sig")


def load_state():
    ensure_data_dir()
    if not os.path.exists(STATE_FILE):
        _, state = init_simulation()
        return state
    with open(STATE_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_state(state):
    ensure_data_dir()
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def get_today_prices(day):
    """현재 day 기준 각 종목의 가격 딕셔너리 반환 {종목: 가격}"""
    df = load_prices_df()
    today = df[df["day"] == day]
    prices = {}
    for p in PRODUCTS.keys():
        row = today[today["product"] == p]
        if not row.empty:
            prices[p] = float(row.iloc[0]["price_end"])
        else:
            # 혹시 누락이면 마지막 가격이라도 사용
            last = df[df["product"] == p].iloc[-1]
            prices[p] = float(last["price_end"])
    return prices


def calc_portfolio_value(holdings, prices):
    return sum(holdings[p] * prices[p] for p in holdings)


# ---------- 라우트들 ----------

@app.route("/")
def index():
    # 메인 화면(매수/매도 + 표) 하나만 사용
    return render_template("index.html")


@app.route("/api/state")
def api_state():
    """현재 게임 상태 + 오늘 가격 반환"""
    state = load_state()
    day = state["day"]
    prices = get_today_prices(day)
    portfolio_value = calc_portfolio_value(state["holdings"], prices)
    total_value = state["cash"] + portfolio_value

    return jsonify({
        "day": day,
        "cash": state["cash"],
        "holdings": state["holdings"],
        "portfolio_value": portfolio_value,
        "total_value": total_value,
        "today_prices": [{"product": p, "price": prices[p]} for p in PRODUCTS.keys()],
        "history": state["history"],
        "max_day": DAYS
    })


@app.route("/api/order", methods=["POST"])
def api_order():
    """
    매수/매도 주문 처리
    body: { "product": "이온음료", "side": "buy"/"sell", "qty": 10 }
    """
    state = load_state()
    data = request.get_json() or {}
    product = data.get("product")
    side = data.get("side")  # "buy" 또는 "sell"
    qty = int(data.get("qty", 0))

    if product not in PRODUCTS:
        return jsonify({"ok": False, "msg": "존재하지 않는 상품입니다."}), 400
    if side not in ("buy", "sell"):
        return jsonify({"ok": False, "msg": "side는 buy 또는 sell이어야 합니다."}), 400
    if qty <= 0:
        return jsonify({"ok": False, "msg": "수량은 1 이상이어야 합니다."}), 400

    day = state["day"]
    prices = get_today_prices(day)
    price = prices[product]
    amount = price * qty

    # 매수
    if side == "buy":
        if state["cash"] < amount:
            return jsonify({"ok": False, "msg": "현금이 부족합니다."}), 400
        state["cash"] -= amount
        state["holdings"][product] += qty

    # 매도
    else:
        if state["holdings"].get(product, 0) < qty:
            return jsonify({"ok": False, "msg": "보유 수량이 부족합니다."}), 400
        state["holdings"][product] -= qty
        state["cash"] += amount

    # 주문 내역 추가
    state["history"].append({
        "day": day,
        "product": product,
        "side": side,
        "qty": qty,
        "price": price,
        "amount": amount
    })

    save_state(state)
    return jsonify({"ok": True})


@app.route("/api/next-day", methods=["POST"])
def api_next_day():
    """다음 날로 이동"""
    state = load_state()
    if state["day"] < DAYS:
        state["day"] += 1
        save_state(state)
        return jsonify({"ok": True, "day": state["day"]})
    else:
        return jsonify({"ok": False, "msg": "마지막 날입니다."})


@app.route("/api/reset-game", methods=["POST"])
def api_reset_game():
    """전체 시뮬레이션과 게임 상태 초기화"""
    init_simulation()
    return jsonify({"ok": True})


@app.route("/download/simulation")
def download_simulation():
    """최신 시뮬레이션 CSV 다운로드(가격 + 매출 데이터)"""
    csv_path = os.path.join(DATA_DIR, "maejeom_simulation_30days.csv")
    if not os.path.exists(csv_path):
        # 없으면 새로 생성
        df, csv_path = run_simulation()
    return send_file(csv_path, as_attachment=True)


if __name__ == "__main__":
    # 앱 시작 시 한 번 시뮬레이션 / 상태 초기화 (파일 없을 때만)
    ensure_data_dir()
    if not os.path.exists(PRICES_FILE) or not os.path.exists(STATE_FILE):
        init_simulation()
    app.run(debug=True)
