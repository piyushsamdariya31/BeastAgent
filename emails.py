"""READ-ONLY email access for any number of accounts (IMAP readonly + BODY.PEEK: nothing is marked read, moved or sent)."""
import imaplib, email
from email.header import decode_header, make_header
from datetime import date, timedelta
from . import accounts
from .log import log

BASE = 10**9  # message id = account_index * BASE + imap_uid (unique across accounts)


def _dec(v):
    return str(make_header(decode_header(v or "")))


def _body(msg, limit=3000):
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain":
                msg = part
                break
        else:
            return ""
    try:
        payload = msg.get_payload(decode=True) or b""
        return payload.decode(msg.get_content_charset() or "utf-8", "ignore")[:limit]
    except Exception:
        return ""


def fetch_new(acct, last_uid, first_run_days=3, max_n=60):
    M = imaplib.IMAP4_SSL(acct["imap_host"], timeout=20)
    try:
        M.login(acct["email"], acct["password"])
        M.select("INBOX", readonly=True)
        if last_uid:
            _, data = M.uid("search", None, f"UID {last_uid + 1}:*")
        else:
            since = (date.today() - timedelta(days=first_run_days)).strftime("%d-%b-%Y")
            _, data = M.uid("search", None, f"SINCE {since}")
        uids = [int(u) for u in data[0].split() if int(u) > last_uid][-max_n:]
        out, newest = [], last_uid
        for uid in uids:
            _, d = M.uid("fetch", str(uid), "(BODY.PEEK[])")
            msg = email.message_from_bytes(d[0][1])
            out.append({"uid": uid, "from": _dec(msg["From"]), "subject": _dec(msg["Subject"]),
                        "date": msg["Date"], "body": _body(msg)})
            newest = max(newest, uid)
        return out, newest
    finally:
        try:
            M.logout()
        except Exception:
            pass


def fetch_all(st):
    """Fetch new mail from every account. st is the state dict (holds last uid per account). Returns (mails, errors)."""
    uids, out, errs = st.setdefault("uids", {}), [], []
    for i, a in enumerate(accounts.load()):
        start = uids.get(a["email"], st.get("last_uid", 0) if i == 0 else 0)
        try:
            ms, newest = fetch_new(a, start)
        except Exception as e:
            log.error(f"{a['email']}: {e}")
            errs.append(f"{a['email']}: {e}")
            continue
        for m in ms:
            m["uid"], m["label"] = i * BASE + m["uid"], a["label"]
        uids[a["email"]] = newest
        out += ms
    log.info(f"Fetched {len(out)} new emails from {len(accounts.load())} account(s)")
    return out, errs
