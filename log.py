import logging
from .config import LOG_FILE

logging.basicConfig(
    filename=LOG_FILE, level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
log = logging.getLogger("agent")

def tail(n=40):
    if not LOG_FILE.exists():
        return []
    return LOG_FILE.read_text(errors="ignore").splitlines()[-n:]
