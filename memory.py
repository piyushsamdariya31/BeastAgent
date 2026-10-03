"""What Beast has learned about you: short facts and preferences you told it. Stored only on this computer."""
import json, re, threading, time, uuid
from .config import DATA

F = DATA / "memory.json"
L = threading.RLock()
SECRET = re.compile(r"(password|passcode|\bpin\b|cvv|card number|\b\d{12,19}\b|api[_ -]?key|secret|token)", re.I)


def load():
    try:
        return json.loads(F.read_text()) if F.exists() else []
    except Exception:
        return []


def add(text):
    text = " ".join(str(text).split())[:220]
    if len(text) < 4:
        raise ValueError("Nothing to remember.")
    if SECRET.search(text):
        raise ValueError("Beast doesn't store passwords, PINs, card numbers or keys.")
    with L:
        ms = load()
        if any(m["text"].lower() == text.lower() for m in ms):
            return "Already known."
        ms.append({"id": uuid.uuid4().hex[:6], "text": text, "t": time.time()})
        F.write_text(json.dumps(ms[-80:]))
    return "Remembered."


def remove(mid):
    with L:
        ms = load()
        left = [m for m in ms if m["id"] != mid and m["text"].lower() != str(mid).lower()]
        F.write_text(json.dumps(left))
        return len(left) != len(ms)


def block():
    ms = load()
    if not ms:
        return ""
    return "WHAT THE USER HAS TAUGHT YOU (their preferences and facts, apply them without being asked):\n" + "\n".join(f'- [{m["id"]}] {m["text"]}' for m in ms)
