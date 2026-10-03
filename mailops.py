"""Email actions beyond reading. Only called after the user approves in the chat."""
import imaplib, smtplib, ssl
from email.message import EmailMessage


def send(a, to, subject, body):
    m = EmailMessage()
    m["From"], m["To"], m["Subject"] = a["email"], to, subject
    m.set_content(body)
    ctx = ssl.create_default_context()
    if int(a["smtp_port"]) == 465:
        with smtplib.SMTP_SSL(a["smtp_host"], 465, context=ctx) as s:
            s.login(a["email"], a["password"])
            s.send_message(m)
    else:
        with smtplib.SMTP(a["smtp_host"], int(a["smtp_port"])) as s:
            s.starttls(context=ctx)
            s.login(a["email"], a["password"])
            s.send_message(m)


def _move(M, u, folder):
    typ, _ = M.uid("COPY", u, f'"{folder}"')
    if typ != "OK":
        raise ValueError(f"Could not copy the message to the folder {folder!r}.")
    M.uid("STORE", u, "+FLAGS", "(\\Deleted)")
    M.expunge()


def act(a, raw_uid, action):
    """action: mark_read | archive | trash"""
    M = imaplib.IMAP4_SSL(a["imap_host"], timeout=20)
    try:
        M.login(a["email"], a["password"])
        M.select("INBOX")
        u, gmail = str(raw_uid), a["imap_host"] == "imap.gmail.com"
        if action == "mark_read":
            M.uid("STORE", u, "+FLAGS", "(\\Seen)")
        elif action == "archive":
            M.uid("STORE", u, "-X-GM-LABELS", "(\\Inbox)") if gmail else _move(M, u, "Archive")
        elif action == "trash":
            if gmail:
                M.uid("STORE", u, "+X-GM-LABELS", "(\\Trash)")
                M.uid("STORE", u, "-X-GM-LABELS", "(\\Inbox)")
            else:
                _move(M, u, "Trash")
        else:
            raise ValueError("Unknown action.")
    finally:
        try:
            M.logout()
        except Exception:
            pass
