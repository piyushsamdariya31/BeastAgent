"""Check a page or a stock on a schedule and say when something changes."""
import re, urllib.request
from html.parser import HTMLParser
from . import llm, quotes, webtask


class _Text(HTMLParser):
    def __init__(self):
        super().__init__()
        self.t, self.skip = [], 0

    def handle_starttag(self, tag, a):
        self.skip += tag in ("script", "style", "noscript")

    def handle_endtag(self, tag):
        self.skip -= tag in ("script", "style", "noscript") and self.skip > 0

    def handle_data(self, d):
        if not self.skip and d.strip():
            self.t.append(d.strip())


def fetch_text(url, browser=False):
    webtask.check_url(url)
    if browser:
        return webtask.page_text(url)
    html = urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"}), timeout=20).read(2_000_000).decode("utf-8", "ignore")
    p = _Text()
    p.feed(html)
    return "\n".join(p.t)


def _price(text):
    r = llm.ask_json('From this web page text, find the main product price. Return {"price": number or null, "currency": "symbol or code"}.\n\n' + text[:6000], 300)
    return r.get("price")


def check(w, st):
    """w: watch spec, st: previous state. Returns (new_state, alert_text_or_None)."""
    k, st = w["kind"], dict(st or {})
    if k == "stock":
        q = quotes.quote(w["symbol"])
        p = q["price"]
        side = "above" if w.get("above") and p >= w["above"] else "below" if w.get("below") and p <= w["below"] else "between"
        alert = f'{w["symbol"]} is {p:,.2f} {q["currency"]}, {side} your {w[side]:,.2f} level.' if side != "between" and st.get("side") != side else None
        return {"side": side, "last": p}, alert
    text = fetch_text(w["url"], w.get("browser", False))
    if k == "price":
        p = _price(text)
        if p is None:
            return st, None
        last, thr = st.get("last"), w.get("threshold")
        below = bool(thr) and p <= thr
        alert = None
        if last is not None and p < last:
            alert = f"Price dropped from {last:,.2f} to {p:,.2f}."
        elif below and not st.get("below"):
            alert = f"Price is {p:,.2f}, at or under your {thr:,.2f} target."
        return {"last": p, "below": below}, alert
    lines = list(dict.fromkeys(l for l in text.split("\n") if len(l) > 20))[:400]
    old = set(st.get("lines", []))
    added = [l for l in lines if l not in old][:8]
    alert = "Page changed. New:\n- " + "\n- ".join(x[:160] for x in added) if old and added else None
    return {"lines": lines}, alert
