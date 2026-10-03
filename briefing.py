import html, webbrowser
from .config import BRIEF_FILE
from .log import tail
from . import todo

def _card(it):
    return (f"<div class=c><b>{html.escape(it['subject'])}</b><br><small>{html.escape(it['from'])}</small>"
            f"<p>{html.escape(it['summary'])}</p><i>{html.escape(it['why'])}</i>"
            + (f"<p>⏰ {html.escape(str(it['deadline']))}</p>" if it.get("deadline") else "") + "</div>")

def render(items, since, n_emails, open_browser=True):
    groups = {"invest": [], "skim": [], "ignore": []}
    for it in items:
        groups.get(it.get("verdict"), groups["skim"]).append(it)
    todos = "".join(f"<li>#{t['id']} {html.escape(t['text'])} <small>({html.escape(t['source'])})</small></li>"
                    for t in todo.open_items()) or "<li>Nothing open 🎉</li>"
    sec = lambda title, key: (f"<h2>{title} ({len(groups[key])})</h2>" + "".join(map(_card, groups[key]))) if groups[key] else ""
    page = f"""<!doctype html><meta charset=utf-8><meta name=viewport content="width=device-width,initial-scale=1">
<title>Briefing</title><style>body{{font:15px system-ui;max-width:800px;margin:2rem auto;padding:0 1rem}}
.c{{border:1px solid #8884;border-radius:8px;padding:.6rem 1rem;margin:.6rem 0}}pre{{background:#8881;padding:1rem;overflow:auto;font-size:12px}}</style>
<h1>While you were away</h1><p>Since <b>{html.escape(str(since))}</b>: <b>{n_emails}</b> new emails.</p>
<h2>✅ To-do</h2><ul>{todos}</ul>
{sec("🔥 Worth your time", "invest")}{sec("👀 Skim", "skim")}{sec("🗑️ Ignore", "ignore")}
<h2>Log (latest)</h2><pre>{html.escape(chr(10).join(tail()))}</pre>"""
    BRIEF_FILE.write_text(page, encoding="utf-8")
    if open_browser:
        webbrowser.open(BRIEF_FILE.as_uri())
    return BRIEF_FILE
