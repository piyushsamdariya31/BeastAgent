"""Stock and index quotes (Yahoo Finance's public chart endpoint; unofficial, may be delayed or change)."""
import json, urllib.parse, urllib.request

ALIAS = {"NIFTY": "^NSEI", "NIFTY50": "^NSEI", "SENSEX": "^BSESN", "BANKNIFTY": "^NSEBANK", "NASDAQ": "^IXIC",
         "SP500": "^GSPC", "S&P500": "^GSPC", "DOW": "^DJI"}


def quote(sym):
    s = ALIAS.get(sym.upper().replace(" ", ""), sym.strip())
    req = urllib.request.Request(f"https://query1.finance.yahoo.com/v8/finance/chart/{urllib.parse.quote(s)}?range=1d&interval=1d",
                                 headers={"User-Agent": "Mozilla/5.0"})
    m = json.load(urllib.request.urlopen(req, timeout=10))["chart"]["result"][0]["meta"]
    p, prev = m["regularMarketPrice"], m.get("chartPreviousClose") or m.get("previousClose")
    return {"symbol": sym, "price": p, "prev": prev, "change_pct": round((p - prev) / prev * 100, 2) if prev else None, "currency": m.get("currency", "")}


def quotes(syms):
    out = []
    for s in list(syms)[:15]:
        try:
            out.append(quote(s))
        except Exception as e:
            out.append({"symbol": s, "error": str(e)[:80]})
    return out


def fmt(q):
    if "error" in q:
        return f'{q["symbol"]}: unavailable ({q["error"]})'
    ch = f' ({q["change_pct"]:+.2f}%)' if q.get("change_pct") is not None else ""
    return f'{q["symbol"]}: {q["price"]:,.2f} {q.get("currency", "")}{ch}'
