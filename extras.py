"""More tools for Beast's chat: calendar, schedules, watches, Discord bot, documents, images, run/test code, summaries, stocks, digest."""
import os, re, uuid
from datetime import datetime, timedelta
from pathlib import Path
from . import accounts, discord_bot, docs, gcal, imagegen, quotes, runner, sched, summarize as summ, watch, webtask, digest

X = {}  # helpers injected by server.py


def bind(**k):
    X.update(k)


def T(name, desc, props=None, req=()):
    return {"name": name, "description": desc, "input_schema": {"type": "object", "properties": props or {}, "required": list(req)}}


s_, i_, n_, b_ = {"type": "string"}, {"type": "integer"}, {"type": "number"}, {"type": "boolean"}
ACC = {"type": "string", "description": "account label or email"}
FILES = {"type": "array", "items": {"type": "object", "properties": {"path": s_, "content": s_}, "required": ["path", "content"]}}
TOOLS = [
    T("calendar_agenda", "Read-only. Show Google Calendar events (all accounts unless one is named) and flag clashes.", {"account": ACC, "date": {"type": "string", "description": "YYYY-MM-DD, default today"}, "days": i_}),
    T("propose_calendar_event", "Propose adding a calendar event with a reminder. Checks for clashes. Needs approval.", {"account": ACC, "title": s_, "start": {"type": "string", "description": "local ISO time, e.g. 2026-10-02T15:00"}, "end": s_, "description": s_, "reminder_minutes": i_}, ["title", "start", "end"]),
    T("stock_quotes", "Read-only. Latest price and day change for stocks/indices (e.g. RELIANCE.NS, AAPL, NIFTY, SENSEX). Facts only, never advice; data may be delayed.", {"symbols": {"type": "array", "items": s_}}, ["symbols"]),
    T("summarize", "Read-only. Condense a long document (PDF/Word/Excel/text path in the home folder) or a web article URL into a short brief.", {"source": s_, "focus": s_}, ["source"]),
    T("run_digest", "Read-only. Build the user's morning digest now: emails, calendar, missions, markets, news."),
    T("list_schedules", "Read-only. List scheduled tasks and watches."),
    T("remove_schedule", "Remove a scheduled task or watch by id.", {"id": s_}, ["id"]),
    T("propose_schedule", "Propose a recurring read-only task: a daily/weekly digest or a prompt to run at a time. Needs approval.", {"name": s_, "task": {"type": "string", "enum": ["digest", "prompt"]}, "at": {"type": "string", "description": "HH:MM 24h"}, "days": {"type": "array", "items": i_, "description": "0=Mon..6=Sun; omit for daily"}, "every_minutes": i_, "prompt": s_}, ["name", "task"]),
    T("propose_watch", "Propose watching a web page price/changes or a stock level on a schedule and alerting the user. Needs approval.", {"name": s_, "kind": {"type": "string", "enum": ["price", "changes", "stock"]}, "url": s_, "symbol": s_, "threshold": n_, "above": n_, "below": n_, "every_minutes": i_, "browser": b_}, ["name", "kind"]),
    T("discord_channels", "Read-only. List channels of the user's own Discord server (bot)."),
    T("discord_read", "Read-only. Recent messages in a channel of the user's own server (bot needs permission).", {"channel": s_, "limit": i_}, ["channel"]),
    T("propose_discord_post", "Propose posting an announcement in the user's own Discord server via the bot. Needs approval.", {"channel": s_, "content": s_}, ["channel", "content"]),
    T("propose_document", "Propose creating a Word (docx) or PDF document (report, playbook, event plan). Needs approval.", {"format": {"type": "string", "enum": ["docx", "pdf"]}, "title": s_, "sections": {"type": "array", "items": {"type": "object", "properties": {"heading": s_, "text": s_, "bullets": {"type": "array", "items": s_}, "table": {"type": "array", "items": {"type": "array", "items": s_}}}}}}, ["format", "title", "sections"]),
    T("propose_image", "Propose generating an image with the user's separate image service (costs their credit). Needs approval.", {"prompt": s_, "size": {"type": "string", "enum": ["1024x1024", "1536x1024", "1024x1536"]}}, ["prompt"]),
    T("propose_edit_files", "Propose adding/overwriting files in an EXISTING project folder (to fix bugs). Needs approval.", {"project": s_, "files": FILES}, ["project", "files"]),
    T("propose_run", "Propose running ONE plain command (python, pytest, pip, node, npm, npx, cargo, go, make) inside a project folder to test it. Needs approval; output is shown afterwards.", {"project": s_, "command": s_}, ["project", "command"]),
    T("close_browser", "Close the browser window Beast left open after a task."),
]
KINDS = {"calendar", "schedule", "watch", "discord", "document", "image", "edit_files", "run"}


def _proj(name):
    d = X["workspace"] / re.sub(r"[^A-Za-z0-9._-]", "-", str(name)).strip(".-")
    if not d.is_dir():
        have = sorted(p.name for p in X["workspace"].iterdir() if p.is_dir()) if X["workspace"].exists() else []
        raise ValueError(f"No project named {name!r}. Existing: {', '.join(have) or 'none'}")
    return d


def _uniq(d, stem, ext):
    d.mkdir(parents=True, exist_ok=True)
    f, n = d / f"{stem}{ext}", 2
    while f.exists():
        f, n = d / f"{stem}-{n}", n + 1
        f = f.with_suffix(ext)
    return f


def _ctx():
    from . import todo
    return {"mails": X["mails"](), "todos": todo.load(), "watchlist": os.getenv("BEAST_WATCHLIST", "").split(","),
            "topics": os.getenv("BEAST_NEWS_TOPICS", "technology, AI and startups")}


def agenda(i, out):
    d0 = (datetime.fromisoformat(i["date"]) if i.get("date") else datetime.now()).replace(hour=0, minute=0, second=0, microsecond=0)
    accs = [X["acct_for"](i["account"])[1]] if i.get("account") else accounts.load()
    lines, allev = [], []
    for a in accs:
        try:
            allev += [{**e, "acct": a["label"]} for e in gcal.list_events(a["email"], d0.isoformat(), (d0 + timedelta(days=int(i.get("days") or 1))).isoformat())]
        except Exception as e:
            lines.append(f'{a["label"]}: {e}')
    for e in sorted(allev, key=lambda e: e["start"]):
        lines.append(f'{e["start"][:16].replace("T", " ")} to {e["end"][11:16] if "T" in e["end"] else "all day"}  {e["title"]} ({e["acct"]})')
    cl = gcal.clashes(allev)
    if cl:
        lines.append("CLASHES: " + "; ".join(f'{a["title"]} overlaps {b["title"]}' for a, b in cl))
    return "\n".join(lines) or "No events."


def event(i, out):
    n, a = X["acct_for"](i.get("account"))
    s, e = gcal._iso(i["start"]), gcal._iso(i["end"])
    if e <= s:
        return "The end must be after the start."
    clash = [x["title"] for x in gcal.list_events(a["email"], s.isoformat(), e.isoformat())]
    rem = int(i.get("reminder_minutes") or 10)
    return X["prop"](out, f'Add to {a["email"]} calendar: "{i["title"]}"\n{s:%a %d %b %H:%M} to {e:%H:%M}, reminder {rem} min before' + (f"\n⚠️ Clashes with: {', '.join(clash)}" if clash else ""),
                     {"kind": "calendar", "acct": n, "title": i["title"], "start": s.isoformat(), "end": e.isoformat(), "desc": str(i.get("description", "")), "rem": rem})


def schedule(i, out):
    at, every, days = i.get("at"), i.get("every_minutes"), i.get("days")
    if not at and not every:
        return "Give a time (HH:MM) or every_minutes."
    if at and not re.fullmatch(r"\d{1,2}:\d{2}", at):
        return "Time must be HH:MM (24h)."
    if i["task"] == "prompt" and not i.get("prompt"):
        return "A prompt is needed."
    when = f"every {every} min" if every and not at else f"at {at} " + ("on " + ",".join("Mon Tue Wed Thu Fri Sat Sun".split()[d] for d in days) if days else "daily")
    return X["prop"](out, f'Schedule "{i["name"]}": {i["task"]} {when}.' + (f'\nPrompt: {i["prompt"]}' if i["task"] == "prompt" else "") +
                     "\nRuns by itself (read-only, it never changes anything) and posts to your chat history with a desktop notification.",
                     {"kind": "schedule", "job": {"name": i["name"], "type": i["task"], "at": at, "days": days, "every": every, "prompt": i.get("prompt")}})


def watch_(i, out):
    k, w = i["kind"], {"kind": i["kind"]}
    if k == "stock":
        if not i.get("symbol") or not (i.get("above") or i.get("below")):
            return "Give a symbol and an above and/or below price."
        w.update(symbol=i["symbol"], above=i.get("above"), below=i.get("below"))
        every, what = max(5, int(i.get("every_minutes") or 30)), f'{i["symbol"]} (above {i.get("above")}, below {i.get("below")})'
    else:
        webtask.check_url(i["url"])
        w.update(url=i["url"], browser=bool(i.get("browser")), threshold=i.get("threshold"))
        every, what = max(30, int(i.get("every_minutes") or 360)), i["url"]
    return X["prop"](out, f'Watch ({k}): {what}\nChecks every {every} min in the background (read-only) and alerts you with a notification and a new chat.',
                     {"kind": "watch", "job": {"name": i["name"], "type": "watch", "every": every, "watch": w}})


def d_post(i, out):
    c = str(i["content"])
    if len(c) > 2000:
        return "Discord limits posts to 2000 characters. Shorten it."
    return X["prop"](out, f'Post in #{str(i["channel"]).lstrip("#")} of your Discord server (no @everyone/@here pings):\n\n{c}', {"kind": "discord", "channel": i["channel"], "content": c})


def document(i, out):
    secs = i["sections"][:40]
    return X["prop"](out, f'Create {i["format"].upper()} "{i["title"]}" with {len(secs)} sections in ~/BeastDocuments:\n' + "\n".join(f'  • {s.get("heading", "(untitled)")}' for s in secs),
                     {"kind": "document", "fmt": i["format"], "title": i["title"], "sections": secs})


def image(i, out):
    return X["prop"](out, f'Generate an image with your image service (uses your credit): "{i["prompt"][:200]}" ({i.get("size", "1024x1024")}). Saved to ~/BeastImages.', {"kind": "image", "prompt": i["prompt"], "size": i.get("size", "1024x1024")})


def edit(i, out):
    d, fl = _proj(i["project"]), X["clean_files"](i["files"])
    return X["prop"](out, f'Update project "{d.name}" ({len(fl)} files):\n' + "\n".join(f'  {"~ overwrite" if (d / f["path"]).exists() else "+ new"} {f["path"]}' for f in fl), {"kind": "edit_files", "project": d.name, "files": fl})


def run_(i, out):
    d = _proj(i["project"])
    runner.check(i["command"], d)
    return X["prop"](out, f'Run in "{d.name}": {i["command"]}\nThis executes code on your computer (2 min limit). The output is shown here afterwards.', {"kind": "run", "project": d.name, "command": i["command"]})


def list_(i, out):
    return "\n".join(f'{j["id"]}: {j["name"]} ({j["type"]}, ' + (f'every {j["every"]} min' if j.get("every") else f'at {j["at"]}') + ")" for j in sched.load()) or "No schedules."


H = {
    "calendar_agenda": agenda, "propose_calendar_event": event, "propose_schedule": schedule, "propose_watch": watch_,
    "stock_quotes": lambda i, o: "\n".join(quotes.fmt(q) for q in quotes.quotes(i["symbols"])),
    "summarize": lambda i, o: summ.summarize(summ.text_of(i["source"], X["safe_path"]), i.get("focus", "")),
    "run_digest": lambda i, o: digest.build(_ctx()), "list_schedules": list_,
    "remove_schedule": lambda i, o: "Removed." if sched.remove(str(i["id"])) else "No schedule with that id.",
    "discord_channels": lambda i, o: ", ".join(c["name"] for c in discord_bot.channels()),
    "discord_read": lambda i, o: "\n".join(f'{m["author"]}: {m["content"]}' for m in reversed(discord_bot.read(i["channel"], i.get("limit", 15)))) or "No messages.",
    "propose_discord_post": d_post, "propose_document": document, "propose_image": image, "propose_edit_files": edit, "propose_run": run_,
    "close_browser": lambda i, o: webtask.close(),
}


def run(name, inp, out):
    h = H.get(name)
    return h(inp, out) if h else None


def execute(p):
    k, accs = p["kind"], accounts.load()
    if k == "calendar":
        return "Added to your calendar: " + (gcal.create(accs[p["acct"]]["email"], p["title"], p["start"], p["end"], p["desc"], p["rem"]) or "done")
    if k in ("schedule", "watch"):
        return f'Scheduled "{p["job"]["name"]}" (id {sched.add(p["job"])}).'
    if k == "discord":
        discord_bot.post(p["channel"], p["content"])
        return "Posted to Discord."
    if k == "document":
        stem = re.sub(r"[^A-Za-z0-9._ -]", "", p["title"]).strip()[:60] or "document"
        f = _uniq(Path(os.getenv("BEAST_DOCS", str(Path.home() / "BeastDocuments"))), stem, "." + p["fmt"])
        (docs.make_docx if p["fmt"] == "docx" else docs.make_pdf)(f, p["title"], p["sections"])
        return f"Created {f}"
    if k == "image":
        return "Image saved: " + imagegen.generate(p["prompt"], p["size"])
    d = _proj(p["project"])
    if k == "edit_files":
        for f in X["clean_files"](p["files"]):
            t = (d / f["path"]).resolve()
            if d.resolve() not in t.parents:
                raise ValueError("Path escapes the project folder.")
            t.parent.mkdir(parents=True, exist_ok=True)
            t.write_text(f["content"], encoding="utf-8")
        return f'Updated {len(p["files"])} files in {d}.'
    if k == "run":
        return runner.run(d, p["command"])
    raise ValueError("Unknown action.")


def run_job(job):
    t = job["type"]
    if t == "digest":
        X["post"](job["name"], digest.build(_ctx()))
    elif t == "prompt":
        X["post"](job["name"], X["readonly_chat"](job["prompt"]))
    elif t == "watch":
        job["state"], alert = watch.check(job["watch"], job.get("state"))
        if alert:
            X["post"](f'🔔 {job["name"]}', alert)
        else:
            X["ev"]("sched", f'{job["name"]}: checked, nothing new')
    return job
