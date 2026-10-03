"""Discord via a BOT in your own server (the allowed route). Needs DISCORD_BOT_TOKEN and DISCORD_GUILD_ID in .env."""
import json, os, urllib.error, urllib.request

API = "https://discord.com/api/v10"


def _req(method, path, body=None):
    tok = os.getenv("DISCORD_BOT_TOKEN")
    if not tok:
        raise RuntimeError("Discord isn't set up. Add DISCORD_BOT_TOKEN and DISCORD_GUILD_ID to .env (see README).")
    r = urllib.request.Request(API + path, method=method, data=None if body is None else json.dumps(body).encode(),
                               headers={"Authorization": "Bot " + tok, "Content-Type": "application/json",
                                        "User-Agent": "DiscordBot (https://localhost/beast, 1.0)"})
    try:
        with urllib.request.urlopen(r, timeout=15) as x:
            return json.loads(x.read() or b"null")
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"Discord said {e.code}: {e.read()[:200].decode(errors='ignore')}")


def channels():
    g = os.getenv("DISCORD_GUILD_ID")
    if not g:
        raise RuntimeError("Add DISCORD_GUILD_ID to .env.")
    return [{"id": c["id"], "name": c["name"]} for c in _req("GET", f"/guilds/{g}/channels") if c["type"] in (0, 5)]


def resolve(ch):
    ch = str(ch).strip().lstrip("#")
    if ch.isdigit():
        return ch
    for c in channels():
        if c["name"].lower() == ch.lower():
            return c["id"]
    raise ValueError("No channel with that name. Known: " + ", ".join(c["name"] for c in channels()))


def read(ch, limit=15):
    return [{"author": m["author"]["username"], "content": m["content"], "time": m["timestamp"]}
            for m in _req("GET", f"/channels/{resolve(ch)}/messages?limit={min(int(limit), 50)}")]


def post(ch, content):
    # allowed_mentions.parse = [] : no @everyone/@here/role/user pings
    return _req("POST", f"/channels/{resolve(ch)}/messages", {"content": content[:2000], "allowed_mentions": {"parse": []}})
