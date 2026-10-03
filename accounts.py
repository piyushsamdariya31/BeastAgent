"""Email accounts: accounts.json (any number) plus the optional single account in .env."""
import json, os
from .config import ROOT, EMAIL, EMAIL_PW, IMAP_HOST

FILE = ROOT / "accounts.json"
HOSTS = {"gmail.com": "imap.gmail.com", "googlemail.com": "imap.gmail.com", "outlook.com": "outlook.office365.com",
         "hotmail.com": "outlook.office365.com", "live.com": "outlook.office365.com", "yahoo.com": "imap.mail.yahoo.com",
         "icloud.com": "imap.mail.me.com", "me.com": "imap.mail.me.com"}


SMTP = {"imap.gmail.com": ("smtp.gmail.com", 465), "outlook.office365.com": ("smtp.office365.com", 587),
        "imap.mail.yahoo.com": ("smtp.mail.yahoo.com", 465), "imap.mail.me.com": ("smtp.mail.me.com", 587)}


def _stored():
    return json.loads(FILE.read_text()) if FILE.exists() else []


def load():
    accs = [dict(a) for a in _stored()]
    if EMAIL and EMAIL_PW and not any(a["email"].lower() == EMAIL.lower() for a in accs):
        env = {"email": EMAIL, "password": EMAIL_PW, "imap_host": IMAP_HOST}
        if os.getenv("DRAFTS_FOLDER"):
            env["drafts"] = os.getenv("DRAFTS_FOLDER")
        accs.insert(0, env)
    for a in accs:
        dom = a["email"].split("@")[-1].lower()
        a.setdefault("imap_host", HOSTS.get(dom, "imap." + dom))
        a.setdefault("drafts", "[Gmail]/Drafts" if a["imap_host"] == "imap.gmail.com" else "Drafts")
        h, pt = SMTP.get(a["imap_host"], ("smtp." + dom, 465))
        a.setdefault("smtp_host", h)
        a.setdefault("smtp_port", pt)
        a["label"] = a.get("name") or a["email"].split("@")[0]
    return accs


def _write(accs):
    FILE.write_text(json.dumps(accs, indent=2))
    try:
        os.chmod(FILE, 0o600)
    except Exception:
        pass


def add(email, password, name="", imap_host="", drafts=""):
    accs = [a for a in _stored() if a["email"].lower() != email.lower()]
    a = {"email": email, "password": password}
    for k, v in (("name", name), ("imap_host", imap_host), ("drafts", drafts)):
        if v:
            a[k] = v
    _write(accs + [a])


def remove(email):
    _write([a for a in _stored() if a["email"].lower() != email.lower()])
