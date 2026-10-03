import json
from datetime import datetime
from .config import STATE_FILE

def load():
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {"last_uid": 0, "last_run": None}

def save(s):
    STATE_FILE.write_text(json.dumps(s, indent=2))

def now():
    return datetime.now().isoformat(timespec="seconds")
