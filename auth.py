"""PIN gate. The PIN is stored only as a salted hash; sessions live in memory (restart = log in again)."""
import hashlib, hmac, json, os, secrets, time
from .config import DATA

F = DATA / "auth.json"
SESS, FAILS, TTL = {}, {"n": 0, "until": 0.0}, 12 * 3600


def is_set():
    return F.exists()


def _hash(pin, salt):
    return hashlib.pbkdf2_hmac("sha256", pin.encode(), salt, 200_000).hex()


def _session():
    t = secrets.token_urlsafe(32)
    SESS[t] = time.time() + TTL
    return t


def setup(pin):
    if is_set():
        raise ValueError("A PIN is already set.")
    if len(pin) < 4:
        raise ValueError("Use at least 4 characters.")
    salt = os.urandom(16)
    F.write_text(json.dumps({"salt": salt.hex(), "hash": _hash(pin, salt)}))
    try:
        os.chmod(F, 0o600)
    except Exception:
        pass
    return _session()


def login(pin):
    if not is_set():
        raise ValueError("Create a PIN first.")
    now = time.time()
    if now < FAILS["until"]:
        raise ValueError(f"Too many attempts. Try again in {int(FAILS['until'] - now) + 1}s.")
    d = json.loads(F.read_text())
    if hmac.compare_digest(_hash(pin, bytes.fromhex(d["salt"])), d["hash"]):
        FAILS["n"] = 0
        return _session()
    FAILS["n"] += 1
    if FAILS["n"] >= 5:
        FAILS["until"] = now + min(300, 30 * 2 ** (FAILS["n"] - 5))
    raise ValueError("Wrong PIN.")


def valid(tok):
    exp = SESS.get(tok)
    if exp and exp > time.time():
        return True
    SESS.pop(tok, None)
    return False
