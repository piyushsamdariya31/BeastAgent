"""One morning brief: emails, calendar, missions, markets and news."""
from datetime import datetime, timedelta
from . import accounts, gcal, llm, quotes


def build(ctx):
    d0 = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    sec = []
    top = [m for m in ctx["mails"] if m["v"] != "ignore"][:8]
    sec.append("EMAILS:\n" + ("\n".join(f'- [{m["v"]} {m["sc"]}] {m["fn"]}: {m["s"]}. {m["sum"]}' + (f' (deadline: {m["d"]})' if m.get("d") else "") for m in top) or "none"))
    evs, note = [], ""
    for a in accounts.load():
        try:
            for e in gcal.list_events(a["email"], d0.isoformat(), (d0 + timedelta(days=1)).isoformat()):
                evs.append({**e, "acct": a["label"]})
        except Exception as e:
            note = f" (calendar unavailable: {str(e)[:80]})"
    cl = gcal.clashes(evs)
    sec.append("CALENDAR TODAY:" + note + "\n" + ("\n".join(f'- {e["start"][11:16] or "all day"} {e["title"]} ({e["acct"]})' for e in sorted(evs, key=lambda e: e["start"])) or "nothing") +
               ("\nCLASHES: " + "; ".join(f'{a["title"]} overlaps {b["title"]}' for a, b in cl) if cl else ""))
    sec.append("MISSIONS:\n" + ("\n".join(f'- {t["text"]}' for t in ctx["todos"] if t["status"] != "done") or "none"))
    wl = [s.strip() for s in ctx.get("watchlist", []) if s.strip()]
    if wl:
        sec.append("MARKETS:\n" + "\n".join(quotes.fmt(q) for q in quotes.quotes(wl)))
    try:
        sec.append("NEWS:\n" + llm.search(f"Top 5 news headlines from today about: {ctx.get('topics', 'technology and AI')}. One line each, with the source name."))
    except Exception as e:
        sec.append(f"NEWS: unavailable ({str(e)[:80]})")
    return llm.ask("Write the user's morning brief from this data. Short sections, plain language, most important first, "
                   "mention any calendar clash or deadline. For markets give facts only, no advice.\n\n" + "\n\n".join(sec), 1500)
