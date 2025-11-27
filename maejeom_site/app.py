from flask import Flask, render_template, request, jsonify, send_file
from simulation.simulator import run_simulation, PRODUCTS, DAYS, EVENTS
import os
import pandas as pd
import json

app = Flask(__name__, instance_relative_config=True)

DATA_DIR = "data"
STATE_FILE = os.path.join(DATA_DIR, "game_state.json")
PRICES_FILE = os.path.join(DATA_DIR, "prices.csv")


def ensure_data_dir():
    os.makedirs(DATA_DIR, exist_ok=True)


def init_simulation():
    """시뮬레이션 + 게임 상태 초기화"""
    ensure_data_dir()
    df, _ = run_simulation()
    df.to_csv(PRICES_FILE, index=False, encoding="utf-8-sig")

    state = {
        "day": 1,
        "cash": 1_000_000,
        "holdings": {p: 0 for p in PRODUCTS.keys()},
        "history": []
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
    df = load_prices_df()
    today = df[df["day"] == day]
    prices = {}
    for p in PRODUCTS.keys():
        row = today[today["product"] == p]
        if not row.empty:
            prices[p] = float(row.iloc[0]["price_end"])
        else:
            last = df[df["product"] == p].iloc[-1]
            prices[p] = float(last["price_end"])
    return prices


def calc_portfolio_value(holdings, prices):
    return sum(holdings[p] * prices[p] for p in holdings)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/state")
def api_state():
    """현재 상태 + 오늘 이벤트 정보 + 가격"""
    state = load_state()
    day = state["day"]
    prices = get_today_prices(day)
    portfolio_value = calc_portfolio_value(state["holdings"], prices)
    total_value = state["cash"] + portfolio_value

    event_info = EVENTS.get(day, {"code": "일반일", "title": "일반적인 수업일", "desc": ""})

    return jsonify({
        "day": day,
        "cash": state["cash"],
        "holdings": state["holdings"],
        "portfolio_value": portfolio_value,
        "total_value": total_value,
        "today_prices": [{"product": p, "price": prices[p]} for p in PRODUCTS.keys()],
        "history": state["history"],
        "max_day": DAYS,
        "event": event_info
    })


@app.route("/api/order", methods=["POST"])
def api_order():
    state = load_state()
    data = request.get_json() or {}
    product = data.get("product")
    side = data.get("side")
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

    if side == "buy":
        if state["cash"] < amount:
            return jsonify({"ok": False, "msg": "현금이 부족합니다."}), 400
        state["cash"] -= amount
        state["holdings"][product] += qty
    else:
        if state["holdings"].get(product, 0) < qty:
            return jsonify({"ok": False, "msg": "보유 수량이 부족합니다."}), 400
        state["holdings"][product] -= qty
        state["cash"] += amount

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
    state = load_state()
    if state["day"] < DAYS:
        state["day"] += 1
        save_state(state)
        event_info = EVENTS.get(state["day"], {"code": "일반일", "title": "일반적인 수업일", "desc": ""})
        return jsonify({"ok": True, "day": state["day"], "event": event_info})
    else:
        return jsonify({"ok": False, "msg": "마지막 날입니다."})


@app.route("/api/reset-game", methods=["POST"])
def api_reset_game():
    init_simulation()
    return jsonify({"ok": True})


@app.route("/download/simulation")
def download_simulation():
    csv_path = os.path.join(DATA_DIR, "maejeom_simulation_30days.csv")
    if not os.path.exists(csv_path):
        df, csv_path = run_simulation()
    return send_file(csv_path, as_attachment=True)


if __name__ == "__main__":
    ensure_data_dir()
    if not os.path.exists(PRICES_FILE) or not os.path.exists(STATE_FILE):
        init_simulation()
    app.run(debug=True)
