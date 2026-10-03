"""Google Sheets for any connected account."""
import re
from . import gcreds

login = gcreds.login


def _svc(email):
    from googleapiclient.discovery import build
    return build("sheets", "v4", credentials=gcreds.credentials(email, "spreadsheets"), cache_discovery=False).spreadsheets()


def sheet_id(x):
    m = re.search(r"/d/([A-Za-z0-9_-]+)", x)
    return m.group(1) if m else x.strip()


def _q(name):
    return "'" + name.replace("'", "''")[:50] + "'"


def create(email, title, tabs):
    s = _svc(email)
    tabs = tabs or [{"name": "Sheet1", "rows": []}]
    r = s.create(body={"properties": {"title": title[:100]},
                       "sheets": [{"properties": {"title": t["name"][:50]}} for t in tabs]}).execute()
    for t in tabs:
        if t.get("rows"):  # RAW: never interpret text as formulas
            s.values().update(spreadsheetId=r["spreadsheetId"], range=_q(t["name"]) + "!A1",
                              valueInputOption="RAW", body={"values": t["rows"]}).execute()
    return r["spreadsheetUrl"]


def read(email, sheet, rng="A1:Z200"):
    return _svc(email).values().get(spreadsheetId=sheet_id(sheet), range=rng).execute().get("values", [])


def write(email, sheet, rng, values, append=False):
    s, sid = _svc(email).values(), sheet_id(sheet)
    if append:
        return s.append(spreadsheetId=sid, range=rng, valueInputOption="RAW", insertDataOption="INSERT_ROWS", body={"values": values}).execute()
    return s.update(spreadsheetId=sid, range=rng, valueInputOption="RAW", body={"values": values}).execute()
