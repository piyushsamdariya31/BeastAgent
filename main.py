"""Beast (command line). READ-ONLY: it reads mail and files you point it to and advises.
It never sends, deletes, moves, or runs anything."""
import argparse
from agent import accounts, emails, triage, todo, state, briefing, files
from agent.log import log

def cmd_brief(a):
    s = state.load()
    log.info(f"Brief started; last run {s['last_run']}")
    try:
        mails, _errs = emails.fetch_all(s)
        items = triage.triage(mails) if mails else []
        for it in items:
            if it.get("todo"):
                todo.add(it["todo"], source=f"email:{it['subject'][:40]}", deadline=it.get("deadline"))
    except Exception as e:
        log.error(f"Brief failed: {e}")
        mails, items = [], []
    since = s["last_run"] or "first run"
    s["last_run"] = state.now()
    state.save(s)
    path = briefing.render(items, since, len(mails), open_browser=not a.no_open)
    print(f"Briefing: {path}")

def cmd_ask(a):
    print(files.ask_about(a.path, a.question))

def cmd_todo(a):
    if a.add: todo.add(a.add)
    if a.done: todo.done(a.done)
    for t in todo.open_items():
        print(f"#{t['id']} {t['text']}  [{t['source']}]")

p = argparse.ArgumentParser()
sub = p.add_subparsers(required=True)
b = sub.add_parser("brief", help="check email + show briefing"); b.add_argument("--no-open", action="store_true"); b.set_defaults(f=cmd_brief)
q = sub.add_parser("ask", help="review a file/folder you choose"); q.add_argument("path"); q.add_argument("question"); q.set_defaults(f=cmd_ask)
t = sub.add_parser("todo"); t.add_argument("--add"); t.add_argument("--done", type=int); t.set_defaults(f=cmd_todo)
def cmd_add(a):
    import getpass
    accounts.add(input("Email address: ").strip(), getpass.getpass("App password (hidden): ").strip(), input("Label, e.g. Work (optional): ").strip())
    print("Added. Restart Beast or press Sync.")
def cmd_accounts(a):
    for x in accounts.load(): print(f"{x['label']:<14}{x['email']}  ({x['imap_host']})")
def cmd_remove(a):
    accounts.remove(a.email); print("Removed.")
sub.add_parser("add-account", help="add another email account").set_defaults(f=cmd_add)
sub.add_parser("accounts", help="list email accounts").set_defaults(f=cmd_accounts)
r = sub.add_parser("remove-account"); r.add_argument("email"); r.set_defaults(f=cmd_remove)
def cmd_glogin(a):
    from agent import gsheets
    for e in ([a.email] if a.email else [x["email"] for x in accounts.load()]):
        print(f"A browser window will open. Sign in as {e} and allow access.")
        gsheets.login(e); print("Google Sheets connected for", e)
g = sub.add_parser("google-login", help="connect Google Sheets for an email account"); g.add_argument("email", nargs="?"); g.set_defaults(f=cmd_glogin)
a = p.parse_args(); a.f(a)
