"""Persistent chat history (data/chats.json)."""
import json, threading, time, uuid
from .config import DATA

F = DATA / "chats.json"
L = threading.RLock()


def load():
    try:
        return json.loads(F.read_text()) if F.exists() else []
    except Exception:
        return []


def save(cs):
    with L:
        F.write_text(json.dumps(cs))


def listing():
    return [{"id": c["id"], "title": c["title"], "updated": c["updated"], "n": len(c["messages"])}
            for c in sorted(load(), key=lambda c: -c["updated"])]


def public(cid):
    for c in load():
        if c["id"] == cid:
            strip = lambda ps: [{k: v for k, v in p.items() if k != "payload"} for p in ps]
            return {**c, "messages": [{**m, "proposals": strip(m.get("proposals", []))} for m in c["messages"]]}


def history(cid):
    c = next((c for c in load() if c["id"] == cid), None)
    out = []
    for m in (c["messages"][-12:] if c else []):
        t = m["content"]
        for p in m.get("proposals") or []:
            t += f"\n[Proposal {p['status']}: {p['summary'].splitlines()[0]}" + (f" -> {p['result']}" if p.get("result") else "") + "]"
        r = m.get("rich") or {}
        if r.get("type") == "pack":
            from . import pack
            pr = pack.get(r.get("run")) or {}
            if pr.get("report"):
                t += "\n[The pack's report: " + pr["report"][:1500] + "]"
        out.append({"role": m["role"], "content": t})
    while out and out[0]["role"] != "user":
        out.pop(0)
    return out


def record(cid, user_text, reply, proposals, rich=None):
    with L:
        cs, now = load(), time.time()
        c = next((c for c in cs if c["id"] == cid), None)
        if not c:
            c = {"id": uuid.uuid4().hex[:10], "title": user_text.strip().replace("\n", " ")[:48] or "Chat",
                 "created": now, "updated": now, "messages": []}
            cs.append(c)
        c["messages"] += [{"role": "user", "content": user_text, "ts": now},
                          {"role": "assistant", "content": reply, "proposals": proposals, "rich": rich, "ts": now}]
        c["updated"] = now
        save(cs)
        return c["id"]


def find(pid):
    cs = load()
    for c in cs:
        for m in c["messages"]:
            for p in m.get("proposals", []):
                if p["id"] == pid:
                    return cs, p
    return cs, None


def delete(cid):
    with L:
        save([c for c in load() if c["id"] != cid])


def add_proposals(cid, run_id, props):
    """Attach requests made by a pack run to the chat message that launched it."""
    with L:
        cs = load()
        for c in cs:
            if c["id"] != cid:
                continue
            for m in c["messages"]:
                if (m.get("rich") or {}).get("run") == run_id:
                    m["proposals"] = (m.get("proposals") or []) + props
                    c["updated"] = time.time()
                    save(cs)
                    return True
    return False
