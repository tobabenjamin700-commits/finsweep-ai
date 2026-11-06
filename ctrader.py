import asyncio, json, uuid, websockets

HOSTS = {"demo": "wss://demo.ctraderapi.com:5036", "live": "wss://live.ctraderapi.com:5036"}
T = dict(APP_AUTH=2100, ACC_AUTH=2102, NEW_ORDER=2106, AMEND=2110, SYMBOLS=2114, SYMBOL_BY_ID=2116,
         DEALS=2133, TRENDBARS=2137, RECONCILE=2124, TRADER=2121, ACC_LIST=2149, ERROR=2142, HEARTBEAT=51)

class CTrader:
    def __init__(self, env, client_id, secret):
        self.url, self.cid, self.secret = HOSTS[env], client_id, secret
        self.pending, self.ws, self.account = {}, None, None

    async def connect(self):
        self.ws = await websockets.connect(self.url)
        asyncio.create_task(self._reader())
        asyncio.create_task(self._heartbeat())
        await self.req(T["APP_AUTH"], {"clientId": self.cid, "clientSecret": self.secret})

    async def _reader(self):
        async for raw in self.ws:
            m = json.loads(raw)
            f = self.pending.pop(m.get("clientMsgId"), None)
            if f and not f.done():
                f.set_result(m)

    async def _heartbeat(self):
        while True:
            await asyncio.sleep(10)
            await self.ws.send(json.dumps({"payloadType": T["HEARTBEAT"], "payload": {}}))

    async def req(self, ptype, payload):
        mid = uuid.uuid4().hex[:12]
        fut = asyncio.get_event_loop().create_future()
        self.pending[mid] = fut
        await self.ws.send(json.dumps({"clientMsgId": mid, "payloadType": ptype, "payload": payload}))
        m = await asyncio.wait_for(fut, 20)
        if m["payloadType"] == T["ERROR"]:
            raise RuntimeError(m["payload"].get("description", "cTrader error"))
        return m["payload"]

    async def login(self, access_token, want_live):
        r = await self.req(T["ACC_LIST"], {"accessToken": access_token})
        accs = r.get("ctidTraderAccount", [])
        pick = next((a for a in accs if bool(a.get("isLive")) == want_live), None)
        if not pick:
            raise RuntimeError("No matching account (check CTRADER_ENV demo/live)")
        self.account = int(pick["ctidTraderAccountId"])
        await self.req(T["ACC_AUTH"], {"ctidTraderAccountId": self.account, "accessToken": access_token})

    async def balance(self):
        t = (await self.req(T["TRADER"], {"ctidTraderAccountId": self.account}))["trader"]
        return t["balance"] / 10 ** t.get("moneyDigits", 2)

    async def symbols(self, names):
        lst = (await self.req(T["SYMBOLS"], {"ctidTraderAccountId": self.account}))["symbol"]
        found = {s["symbolName"].replace("/", "").upper(): s["symbolId"] for s in lst}
        ids = {n: found[n] for n in names if n in found}
        det = (await self.req(T["SYMBOL_BY_ID"], {"ctidTraderAccountId": self.account, "symbolId": list(ids.values())}))["symbol"]
        return ids, {d["symbolId"]: d for d in det}

    async def candles(self, sid, count=120):
        import time
        now = int(time.time() * 1000)
        r = await self.req(T["TRENDBARS"], {"ctidTraderAccountId": self.account, "symbolId": sid, "period": 5,
                                            "fromTimestamp": now - count * 5 * 60000, "toTimestamp": now})
        out = []
        for b in r.get("trendbar", []):
            lo = b["low"]
            out.append({"t": b["utcTimestampInMinutes"], "l": lo / 1e5, "o": (lo + b.get("deltaOpen", 0)) / 1e5,
                        "h": (lo + b.get("deltaHigh", 0)) / 1e5, "c": (lo + b.get("deltaClose", 0)) / 1e5})
        return out

    async def market_order(self, sid, side, volume, sl_dist, tp_dist):
        return await self.req(T["NEW_ORDER"], {"ctidTraderAccountId": self.account, "symbolId": sid, "orderType": 1,
                              "tradeSide": 1 if side == "BUY" else 2, "volume": volume,
                              "relativeStopLoss": int(sl_dist * 1e5), "relativeTakeProfit": int(tp_dist * 1e5)})

    async def positions(self):
        return (await self.req(T["RECONCILE"], {"ctidTraderAccountId": self.account})).get("position", [])

    async def amend_sl(self, pos, new_sl):
        p = {"ctidTraderAccountId": self.account, "positionId": pos["positionId"], "stopLoss": new_sl}
        if pos.get("takeProfit"):
            p["takeProfit"] = pos["takeProfit"]
        return await self.req(T["AMEND"], p)

    async def deals(self, days=30):
        import time
        now = int(time.time() * 1000)
        r = await self.req(T["DEALS"], {"ctidTraderAccountId": self.account, "fromTimestamp": now - days * 86400000,
                                        "toTimestamp": now, "maxRows": 100})
        return r.get("deal", [])
