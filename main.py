import asyncio, os, time, traceback
from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from ctrader import CTrader
from strategy import analyze

SYMS = ["XAUUSD", "EURUSD"]
ENV = os.getenv("CTRADER_ENV", "demo")
SECRET = os.getenv("ENGINE_SECRET", "change-me")
RISK_PCT = 0.01

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

S = {"connected": False, "balance": 0, "initial": float(os.getenv("INITIAL_CAPITAL", 0)), "signals": {},
     "error": None, "prices": {}}
ct: CTrader | None = None
traded = set()

def sid_to_name(ids):
    return {v: k for k, v in ids.items()}

async def run(token):
    global ct
    ct = CTrader(ENV, os.environ["CTRADER_CLIENT_ID"], os.environ["CTRADER_CLIENT_SECRET"])
    await ct.connect()
    await ct.login(token, ENV == "live")
    ids, det = await ct.symbols(SYMS)
    S["connected"], S["error"] = True, None
    while True:
        try:
            bal = await ct.balance()
            S["balance"] = bal
            if not S["initial"]:
                S["initial"] = bal                      # lock initial capital on first sight
            profit = bal - S["initial"]
            open_pos = await ct.positions()
            open_ids = {p["tradeData"]["symbolId"] for p in open_pos}
            for name, sid in ids.items():
                cs = await ct.candles(sid)
                if len(cs) < 31:
                    continue
                closed = cs[:-1] + [cs[-1]]            # last bar used as live price
                S["prices"][sid] = cs[-1]["c"]
                res = analyze(closed)
                if res["signal"] != "WAIT":
                    if profit <= 0:
                        res = {"signal": "WAIT", "explanation": "Capital locked: no house money (profit) available."}
                    elif sid in open_ids:
                        res = {"signal": "WAIT", "explanation": "Trade already open on this symbol."}
                    elif res["key"] in traded:
                        res = {"signal": "WAIT", "explanation": "Setup already traded."}
                    else:
                        risk_money = min(RISK_PCT * bal, profit)   # never risk initial capital
                        dist = abs(res["entry"] - res["sl"])
                        d = det[sid]
                        units = risk_money / dist                   # USD-quoted pairs, USD account
                        step = d.get("stepVolume", 1)
                        vol = int(units * 100 // step * step)
                        vol = max(vol, d.get("minVolume", step))
                        if vol * dist / 100 > profit * 1.5:         # min lot would over-risk
                            res = {"signal": "WAIT", "explanation": "Min lot size exceeds house-money risk."}
                        else:
                            await ct.market_order(sid, res["signal"], vol, dist, 2 * dist)
                            traded.add(res["key"])
                S["signals"][name] = res
            # breakeven at 1R
            for p in open_pos:
                sid = p["tradeData"]["symbolId"]
                px, entry, sl = S["prices"].get(sid), p["price"], p.get("stopLoss")
                if not px or not sl:
                    continue
                r = abs(entry - sl)
                buy = str(p["tradeData"]["tradeSide"]) in ("1", "BUY")
                if r > 1e-6 and ((buy and sl < entry and px - entry >= r) or (not buy and sl > entry and entry - px >= r)):
                    await ct.amend_sl(p, entry)
            S["error"] = None
        except Exception as e:
            S["error"] = str(e); traceback.print_exc()
        await asyncio.sleep(15)

@app.get("/health")
def health():
    return {"ok": True}

@app.post("/token")
async def token(body: dict, x_engine_secret: str = Header(None)):
    if x_engine_secret != SECRET:
        raise HTTPException(401)
    asyncio.create_task(run(body["accessToken"]))
    return {"started": True}

@app.on_event("startup")
async def boot():
    if os.getenv("CTRADER_ACCESS_TOKEN"):
        asyncio.create_task(run(os.environ["CTRADER_ACCESS_TOKEN"]))

@app.get("/status")
def status():
    return {**S, "profit": S["balance"] - S["initial"], "prices": None}

@app.get("/history")
async def history():
    if not ct or not S["connected"]:
        return {"open": [], "closed": []}
    pos = await ct.positions()
    deals = await ct.deals()
    return {"open": [{"id": p["positionId"], "symbolId": p["tradeData"]["symbolId"], "side": p["tradeData"]["tradeSide"],
                      "volume": p["tradeData"]["volume"] / 100, "entry": p["price"], "sl": p.get("stopLoss"), "tp": p.get("takeProfit")} for p in pos],
            "closed": [{"id": d["dealId"], "symbolId": d["symbolId"], "side": d["tradeSide"], "price": d["executionPrice"],
                        "pnl": d["closePositionDetail"]["grossProfit"] / 100, "time": d["executionTimestamp"]}
                       for d in deals if d.get("closePositionDetail")]}
