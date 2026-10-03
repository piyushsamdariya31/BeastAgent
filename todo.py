import json
from .config import TODO_FILE
from .state import now

def load():
    return json.loads(TODO_FILE.read_text()) if TODO_FILE.exists() else []

def save(items):
    TODO_FILE.write_text(json.dumps(items, indent=2))

def add(text, source="manual", deadline=None):
    items = load()
    if any(t["text"] == text and t["source"] == source for t in items):
        return
    nid = max([t["id"] for t in items], default=0) + 1
    items.append({"id": nid, "text": text, "source": source, "deadline": deadline,
                  "status": "open", "created": now()})
    save(items)

def done(tid):
    items = load()
    for t in items:
        if t["id"] == tid:
            t["status"] = "done"
    save(items)

def open_items():
    return [t for t in load() if t["status"] == "open"]


def toggle(tid):
    items = load()
    for t in items:
        if t["id"] == tid:
            t["status"] = "open" if t["status"] == "done" else "done"
    save(items)
