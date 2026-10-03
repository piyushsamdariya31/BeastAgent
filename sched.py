"""Scheduled jobs (data/schedules.json). The server's scheduler thread calls tick() every 30s."""
import json, threading, time, uuid
from datetime import datetime, timedelta
from .config import DATA

F = DATA / "schedules.json"
L = threading.RLock()


def load():
    try:
        return json.loads(F.read_text()) if F.exists() else []
    except Exception:
        return []


def _save(js):
    with L:
        F.write_text(json.dumps(js))


def add(job):
    with L:
        job = {**job, "id": uuid.uuid4().hex[:6], "state": {}, "last_run": None}
        _save(load() + [job])
        return job["id"]


def update(job):
    with L:
        _save([job if j["id"] == job["id"] else j for j in load()])


def remove(jid):
    with L:
        js = load()
        _save([j for j in js if j["id"] != jid])
        return len(js) != len(load())


def is_due(j, now):
    last = j.get("last_run")
    if j.get("every"):
        return last is None or now.timestamp() - last >= int(j["every"]) * 60
    h, m = map(int, j["at"].split(":"))
    at = now.replace(hour=h, minute=m, second=0, microsecond=0)
    if j.get("days") and now.weekday() not in j["days"]:
        return False
    # catch up if the laptop was off at that time, but not if it's more than 12h late
    return at <= now < at + timedelta(hours=12) and (last is None or last < at.timestamp())


def tick(run, now=None):
    now = now or datetime.now()
    for j in load():
        if is_due(j, now):
            j["last_run"] = time.time()
            update(j)
            j = run(j) or j
            j["last_run"] = j.get("last_run") or time.time()
            update(j)
