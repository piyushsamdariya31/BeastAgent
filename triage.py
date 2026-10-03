import json
from . import llm
from .log import log

PROMPT = """Triage these emails. For each return an object:
{{"uid": int, "summary": "1 sentence", "verdict": "invest" | "skim" | "ignore",
  "score": 0-100 (how worth the user's time), "why": "short reason it is/isn't worth the user's time", "deadline": "date or null",
  "todo": "concrete action for the user, or null"}}
Return {{"items": [...]}}.

EMAILS:
{emails}"""

def triage(emails):
    items = []
    for i in range(0, len(emails), 20):
        batch = emails[i:i + 20]
        try:
            res = llm.ask_json(PROMPT.format(emails=json.dumps(batch, ensure_ascii=False)))
            items += res.get("items", [])
        except Exception as e:
            log.error(f"Triage batch failed: {e}")
    meta = {e["uid"]: e for e in emails}
    for it in items:
        m = meta.get(it["uid"], {})
        it["from"], it["subject"] = m.get("from", ""), m.get("subject", "")
        it["body"], it["date"], it["label"] = m.get("body", ""), m.get("date"), m.get("label")
    return items
