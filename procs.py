"""Run generated apps (Node or Python) in the background with live logs. Started only from an explicit click."""
import atexit, os, re, signal, socket, subprocess, sys, threading, time
from collections import deque
from . import runner

P = {}
L = threading.Lock()


def _free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _env(port):
    e = {k: v for k, v in os.environ.items() if k in runner.KEEP or k.startswith("LC_")}
    e.update(PORT=str(port), HOST="127.0.0.1", NODE_ENV="development", PYTHONUNBUFFERED="1")
    return e


def _venv_py(d):
    return str(d / (".venv/Scripts/python.exe" if os.name == "nt" else ".venv/bin/python"))


def commands(d, stack, install, start, port):
    """Turn the project's install/start commands into concrete, checked commands."""
    rel = ".venv\\Scripts\\python.exe" if os.name == "nt" else ".venv/bin/python"
    ins, st = list(install or []), (start or "").strip()
    if stack == "node":
        ins = ins or ["npm install"]
        st = st or "npm start"
    elif stack == "python":
        if not ins and (d / "requirements.txt").exists():
            ins = ["pip install -r requirements.txt"]
        ins = [re.sub(r"^(pip3?|python3? -m pip)\b", rel + " -m pip", c) for c in ins]
        st = re.sub(r"^python3?\b", rel, st or "python app.py")
    else:
        raise ValueError("Static projects don't need running: they preview instantly.")
    ins, st = [c.replace("{PORT}", str(port)) for c in ins], st.replace("{PORT}", str(port))
    for c in ins + [st]:
        runner.check(c, d)
    return ins, st


def _log(p, line):
    p["log"].append(line.rstrip("\n")[:400])


def _kill(proc):
    if not proc or proc.poll() is not None:
        return
    try:
        if os.name == "nt":
            subprocess.run(["taskkill", "/T", "/F", "/PID", str(proc.pid)], capture_output=True)
        else:
            os.killpg(proc.pid, signal.SIGTERM)
            try:
                proc.wait(5)
            except subprocess.TimeoutExpired:
                os.killpg(proc.pid, signal.SIGKILL)
    except Exception:
        proc.kill()


def _popen(args, d, env):
    kw = {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP} if os.name == "nt" else {"start_new_session": True}
    return subprocess.Popen(args, cwd=str(d), env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1, **kw)


def _args(cmd, d):
    import shlex, shutil
    a = runner.check(cmd, d)
    if "/" not in a[0] and "\\" not in a[0]:
        a[0] = shutil.which(a[0]) or a[0]
    else:
        a[0] = os.path.abspath(os.path.join(str(d), a[0]))  # keep the venv symlink
    return a


def start(name, d, stack, install, start_cmd):
    with L:
        cur = P.get(name)
        if cur and cur["status"] in ("installing", "starting", "running"):
            return status(name)
        port = _free_port()
        ins, st = commands(d, stack, install, start_cmd, port)
        p = P[name] = {"status": "installing", "port": port, "url": None, "log": deque(maxlen=500), "proc": None, "cmds": ins + [st], "error": None}
    threading.Thread(target=_run, args=(p, d, stack, ins, st), daemon=True).start()
    return status(name)


def _run(p, d, stack, ins, st):
    env = _env(p["port"])
    try:
        if stack == "python" and not os.path.exists(_venv_py(d)):
            _log(p, "$ python -m venv .venv")
            r = subprocess.run([sys.executable, "-m", "venv", ".venv"], cwd=str(d), capture_output=True, text=True, timeout=300)
            if r.returncode:
                raise RuntimeError("Couldn't create the virtual environment: " + (r.stderr or r.stdout)[-300:])
        for c in ins:
            if p["status"] == "stopped":
                return
            _log(p, "$ " + c)
            pr = p["proc"] = _popen(_args(c, d), d, env)
            for line in pr.stdout:
                _log(p, line)
            if pr.wait() != 0:
                raise RuntimeError(f"`{c}` failed (exit {pr.returncode}). See the log.")
        if p["status"] == "stopped":
            return
        p["status"] = "starting"
        _log(p, "$ " + st)
        pr = p["proc"] = _popen(_args(st, d), d, env)
        threading.Thread(target=lambda: [_log(p, l) for l in pr.stdout], daemon=True).start()
        t0 = time.time()
        while time.time() - t0 < 120:
            if pr.poll() is not None:
                raise RuntimeError(f"The app stopped (exit {pr.returncode}). See the log.")
            try:
                with socket.create_connection(("127.0.0.1", p["port"]), timeout=1):
                    p.update(status="running", url=f"http://127.0.0.1:{p['port']}/")
                    return
            except OSError:
                time.sleep(0.7)
        raise RuntimeError(f"The app didn't start listening on port {p['port']} within 2 minutes. It must read the PORT environment variable.")
    except Exception as e:
        if p["status"] != "stopped":
            p.update(status="failed", error=str(e))
            _log(p, "! " + str(e))
            _kill(p.get("proc"))


def stop(name):
    p = P.get(name)
    if p:
        p["status"] = "stopped"
        _kill(p.get("proc"))
        p["url"] = None
    return status(name)


def status(name):
    p = P.get(name)
    if not p:
        return {"status": "stopped", "url": None, "log": [], "error": None}
    return {"status": p["status"], "url": p["url"], "port": p["port"], "log": list(p["log"])[-200:], "error": p["error"], "cmds": p["cmds"]}


@atexit.register
def stop_all():
    for n in list(P):
        stop(n)
