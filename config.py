import os
from pathlib import Path
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

DATA = ROOT / "data"
LOGS = ROOT / "logs"
DATA.mkdir(exist_ok=True)
LOGS.mkdir(exist_ok=True)

STATE_FILE = DATA / "state.json"
TODO_FILE = DATA / "todo.json"
BRIEF_FILE = DATA / "briefing.html"
LOG_FILE = LOGS / "agent.log"

MODEL = os.getenv("MODEL", "claude-sonnet-5-5")
IMAP_HOST = os.getenv("IMAP_HOST", "imap.gmail.com")
EMAIL = os.getenv("EMAIL_ADDRESS", "")
EMAIL_PW = os.getenv("EMAIL_APP_PASSWORD", "")
MY_CONTEXT = os.getenv("MY_CONTEXT", "")
