"""Every Claude model your API key can use, fetched live from the API. 'auto' lets Beast pick the right one per job."""
import json, os, threading, time
from .config import DATA

F = DATA / "settings.json"
L = threading.Lock()
FALLBACK = [{"id": "claude-fable-5-1", "name": "Claude Fable 5.1"}, {"id": "claude-opus-5-5", "name": "Claude Opus 5.5"},
            {"id": "claude-sonnet-5-5", "name": "Claude Sonnet 5.5"}, {"id": "claude-haiku-4-5-20251001", "name": "Claude Haiku 4.5"}]
TIERS = {"fast": ("haiku", "sonnet", "opus"), "balanced": ("sonnet", "opus", "haiku"), "deep": ("opus", "sonnet", "haiku")}
ENV = {"fast": "FAST_MODEL", "balanced": "MODEL", "deep": "BUILD_MODEL"}
_cache = {"t": 0.0, "models": None, "live": False}


def available(force=False):
    """Models for this API key, newest first. Falls back to a built-in list if the API can't be reached."""
    with L:
        if _cache["models"] and not force and time.time() - _cache["t"] < 3600:
            return _cache["models"]
        try:
            from . import llm
            ms = []
            for m in llm.client().models.list(limit=100):
                ms.append({"id": m.id, "name": getattr(m, "display_name", None) or m.id, "created": str(getattr(m, "created_at", "") or "")})
                if len(ms) >= 200:
                    break
            if not ms:
                raise RuntimeError("empty")
            ms.sort(key=lambda m: m["created"], reverse=True)
            _cache.update(models=ms, live=True, t=time.time())
        except Exception:
            _cache.update(models=[dict(m) for m in FALLBACK], live=False, t=time.time() - 3300)  # retry in 5 minutes
        return _cache["models"]


def _settings():
    try:
        return json.loads(F.read_text()) if F.exists() else {}
    except Exception:
        return {}


def current():
    return _settings().get("model", "auto")


def choose(model):
    model = str(model)
    if model != "auto" and model not in {m["id"] for m in available()}:
        raise ValueError("That model isn't available for your API key.")
    with L:
        F.write_text(json.dumps({**_settings(), "model": model}))
    return model


def tier_model(tier):
    """What Auto uses for a tier: your .env override if set, else the newest model of the matching family."""
    if os.getenv(ENV.get(tier, "")):
        return os.getenv(ENV[tier])
    ms = available()
    for fam in TIERS.get(tier, TIERS["balanced"]):
        for m in ms:
            if fam in m["id"]:
                return m["id"]
    return ms[0]["id"]


def pick(tier="balanced"):
    """The model to use right now: your chosen model, or in Auto the best fit for this kind of job."""
    cur = current()
    return tier_model(tier) if cur == "auto" else cur


def public():
    ms = available()
    return {"current": current(), "live": _cache["live"], "models": [{"id": m["id"], "name": m["name"]} for m in ms],
            "auto": {t: tier_model(t) for t in TIERS}}
