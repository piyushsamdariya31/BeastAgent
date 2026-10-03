"""Google OAuth shared by Sheets and Calendar. One-time per account: python main.py google-login <email>"""
import os
from .config import DATA, ROOT

CLIENT = ROOT / "google_client.json"
TOK = DATA / "google"
SCOPES = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/calendar"]


def login(email):
    from google_auth_oauthlib.flow import InstalledAppFlow
    if not CLIENT.exists():
        raise FileNotFoundError("Put your Google OAuth client file at google_client.json (see README).")
    creds = InstalledAppFlow.from_client_secrets_file(str(CLIENT), SCOPES).run_local_server(port=0)
    TOK.mkdir(parents=True, exist_ok=True)
    f = TOK / f"{email}.json"
    f.write_text(creds.to_json())
    try:
        os.chmod(f, 0o600)
    except Exception:
        pass


def credentials(email, need):
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    f = TOK / f"{email}.json"
    if not f.exists():
        raise RuntimeError(f"Google isn't connected for {email}. Run: python main.py google-login {email}")
    c = Credentials.from_authorized_user_file(str(f))
    if not any(need in s for s in (c.scopes or [])):
        raise RuntimeError(f"{email} needs new Google permissions. Run again: python main.py google-login {email}")
    if not c.valid and c.refresh_token:
        c.refresh(Request())
        f.write_text(c.to_json())
    return c
