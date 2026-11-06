"""Liquidity sweep -> BOS -> Fib 0.50-0.75 pullback. Candles: dicts with t,o,h,l,c (oldest first)."""

def _swing_highs(c, n=3):
    return [i for i in range(n, len(c) - n)
            if c[i]["h"] == max(x["h"] for x in c[i - n:i + n + 1])]

def _swing_lows(c, n=3):
    return [i for i in range(n, len(c) - n)
            if c[i]["l"] == min(x["l"] for x in c[i - n:i + n + 1])]

def _bearish_setup(c):
    """Look for sweep of swing high + BOS down. Returns setup dict or None."""
    price = c[-1]["c"]
    sh, sl_ = _swing_highs(c), _swing_lows(c)
    start = max(0, len(c) - 40)
    for k in range(len(c) - 2, start, -1):                    # newest sweep first
        prior = [i for i in sh if i < k - 1]
        lows = [i for i in sl_ if i < k]
        if not prior or not lows:
            continue
        H = c[prior[-1]]["h"]
        if not (c[k]["h"] > H and c[k]["c"] < H):             # wick past high, close back below
            continue
        L = c[lows[-1]]["l"]
        j = next((x for x in range(k + 1, len(c)) if c[x]["c"] < L), None)  # BOS
        if j is None:
            return {"stage": "sweep", "key": c[k]["t"]}
        hi = max(x["h"] for x in c[k:j + 1])
        lo = min(x["l"] for x in c[k:])
        rng = hi - lo
        if rng <= 0 or price > hi:
            return None                                        # invalidated
        return {"stage": "bos", "key": c[k]["t"], "hi": hi, "lo": lo,
                "zone_lo": lo + 0.50 * rng, "zone_hi": lo + 0.75 * rng,
                "sl": hi + 0.05 * rng}
    return None

def analyze(candles):
    """Returns {signal: BUY|SELL|WAIT, explanation, entry, sl, tp, key}."""
    if len(candles) < 30:
        return {"signal": "WAIT", "explanation": "Not enough candle data yet."}
    price = candles[-1]["c"]
    inv = [{"t": x["t"], "o": -x["o"], "h": -x["l"], "l": -x["h"], "c": -x["c"]} for x in candles]
    for side, data, sign in (("SELL", candles, 1), ("BUY", inv, -1)):
        s = _bearish_setup(data)                               # BUY = mirrored SELL
        if not s:
            continue
        if s["stage"] == "sweep":
            kind = "high" if side == "SELL" else "low"
            return {"signal": "WAIT", "explanation": f"Liquidity sweep of swing {kind} detected. Waiting for Break of Structure."}
        zl, zh = sorted((sign * s["zone_lo"], sign * s["zone_hi"]))
        sl = sign * s["sl"]
        if zl <= price <= zh:
            risk = abs(price - sl)
            tp = price - 2 * risk if side == "SELL" else price + 2 * risk
            return {"signal": side, "explanation": f"BOS confirmed. Price in Fib 0.50-0.75 zone ({zl:.5f}-{zh:.5f}). Entering {side}.",
                    "entry": price, "sl": sl, "tp": tp, "key": f"{side}-{s['key']}"}
        where = "retrace" if (side == "SELL" and price < zl) or (side == "BUY" and price > zh) else "pullback"
        return {"signal": "WAIT", "explanation": f"{side} setup valid. Waiting for Fib {where} into {zl:.5f}-{zh:.5f}."}
    return {"signal": "WAIT", "explanation": "Scanning for liquidity sweep."}
