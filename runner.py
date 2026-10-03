"""Run and test code inside a project folder. Only after the user approves the exact command."""
import os, re, shlex, shutil, subprocess
from pathlib import Path

ALLOWED = {"python", "python3", "pytest", "pip", "pip3", "node", "npm", "npx", "cargo", "go", "make"}
BAD = re.compile(r"[;&|<>`$\n\r]")
DENY = {"publish", "upload", "deploy", "login", "-c", "-e", "--eval"}
KEEP = {"PATH", "HOME", "USERPROFILE", "SYSTEMROOT", "TEMP", "TMP", "TMPDIR", "LANG", "APPDATA", "LOCALAPPDATA", "PATHEXT", "COMSPEC"}


def check(cmd, cwd=None):
    if BAD.search(cmd):
        raise ValueError("Give one plain command (no ; & | > < ` $).")
    args = shlex.split(cmd, posix=(os.name != "nt"))
    if not args:
        raise ValueError("Empty command.")
    if "/" in args[0] or "\\" in args[0]:  # e.g. .venv/bin/python must live inside the project
        base = os.path.abspath(str(cwd)) if cwd is not None else None
        exe_path = os.path.abspath(os.path.join(base or "", args[0]))  # no resolve(): venv pythons are symlinks
        if base is None or not exe_path.startswith(base + os.sep) or ".." in Path(args[0]).parts:
            raise ValueError("Only programs inside the project folder can be run by path.")
    exe = Path(args[0]).name.lower().removesuffix(".exe").removesuffix(".cmd")
    if exe not in ALLOWED:
        raise ValueError("Allowed commands: " + ", ".join(sorted(ALLOWED)))
    if any(a.lower() in DENY for a in args[1:]):
        raise ValueError("That option isn't allowed (publish/upload/deploy/login/-c/-e).")
    return args


def run(cwd, cmd, timeout=120):
    args = check(cmd, cwd)
    if not (os.sep in args[0] or "/" in args[0]):
        args[0] = shutil.which(args[0]) or args[0]
    env = {k: v for k, v in os.environ.items() if k in KEEP or k.startswith("LC_")}
    try:
        r = subprocess.run(args, cwd=str(cwd), capture_output=True, text=True, timeout=timeout, env=env)
        out, code = (r.stdout or "") + (r.stderr or ""), r.returncode
    except subprocess.TimeoutExpired as e:
        raw = e.stdout or b""
        out, code = (raw.decode(errors="ignore") if isinstance(raw, bytes) else raw) + f"\n(stopped after {timeout}s)", "timeout"
    except FileNotFoundError:
        out, code = f"{args[0]} isn't installed on this computer.", "not found"
    return f"exit code {code}\n" + out[-3500:]
