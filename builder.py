"""Beast Studio: build websites, landing pages, apps and games from a prompt, with Claude through your API key.

A build is a background job: plan the project, write each file, then snapshot it as version 1.
A change ("make the hero darker") reads the current files, applies the edit and snapshots a new version.
Every version can be undone. Builds only ever create new folders inside the workspace.
"""
import json, os, re, shutil, threading, time, uuid
from pathlib import Path
from . import llm
from .config import DATA
from .log import log

WORKSPACE = Path(os.getenv("BEAST_WORKSPACE", str(Path.home() / "BeastProjects")))
MAXTOK = int(os.getenv("BUILD_MAX_TOKENS", "32000"))
REG = DATA / "projects.json"
VERS = DATA / "versions"
SKIP = {"node_modules", ".venv", "venv", "__pycache__", ".git", "dist", "build", ".next", ".beast"}
TEXT = {".html", ".htm", ".css", ".js", ".mjs", ".cjs", ".jsx", ".ts", ".tsx", ".json", ".md", ".txt", ".py", ".svg",
        ".xml", ".yml", ".yaml", ".toml", ".env.example", ".gitignore", ".csv", ".sql", ".sh", ".ini", ".cfg"}
KINDS = {"landing": "landing page", "website": "website", "app": "web app", "dashboard": "dashboard",
         "game": "browser game", "tool": "small tool", "api": "backend API", "auto": "whatever fits best"}
STYLES = {"editorial": "editorial: expressive serif display type, generous whitespace, magazine-like rhythm",
          "minimal": "minimal: restrained palette, precise spacing, one accent colour, quiet confidence",
          "bold": "bold: big type, strong colour blocks, high contrast, energetic",
          "playful": "playful: friendly rounded shapes, warm colours, small delightful animations",
          "auto": "choose the direction that best fits the subject"}
L = threading.RLock()
JOBS = {}

GUIDE = """You are the builder inside Beast, a personal agent. You turn a request into a complete, working project on the user's laptop.

Quality bar
- Build exactly what was asked. Every file is complete and working: no placeholders, TODOs, stubs or lorem ipsum.
- Write real, specific copy for the subject (product names, prices in the right currency, plausible details). Keep it honest: no fake awards, press logos or invented statistics presented as real.
- Design with a point of view that fits the subject: a deliberate palette, a characterful display face paired with a readable body face (Google Fonts is fine), a clear type scale and real hierarchy. Avoid generic templates and purple-to-blue gradient heroes.
- Responsive down to 360px wide, keyboard accessible, visible focus, sufficient contrast, alt text and form labels, respects prefers-reduced-motion.
- Illustrate with CSS, inline SVG or canvas. Do not hotlink external images unless the user supplied the URL.

Stack choice
- "static" (preferred): plain HTML, CSS and JavaScript with index.html at the root. Use this for landing pages, websites, portfolios, games, dashboards and front-end apps. Libraries may load from cdnjs.cloudflare.com, cdn.jsdelivr.net or unpkg.com with pinned versions (React and Chart.js have UMD builds). Persist app data in localStorage, wrapped in try/catch.
- "node": only when a real server is needed (shared database, server-side API, auth). Express, static files in public/, port from process.env.PORT, an "npm start" script, exact dependency versions in package.json.
- "python": Flask when the user asks for Python. app.py reads the port from the PORT environment variable; requirements.txt with pinned versions.
- Never require secrets. If a feature needs an API key, read it from an environment variable, document it in the README and degrade gracefully without it.

Files
- Relative paths only, at most 25 files, sensible structure. Always include a short README.md: what it is and how to run it.
"""

PLAN_TOOL = {"name": "plan_project", "description": "Plan the project before writing any file.", "input_schema": {
    "type": "object", "required": ["name", "title", "summary", "stack", "files", "design"],
    "properties": {
        "name": {"type": "string", "description": "short kebab-case folder name"},
        "title": {"type": "string", "description": "the project's display name"},
        "summary": {"type": "string", "description": "one or two sentences on what it is"},
        "stack": {"type": "string", "enum": ["static", "node", "python"]},
        "design": {"type": "string", "description": "palette (hex), typefaces, layout concept and the one memorable element"},
        "files": {"type": "array", "items": {"type": "object", "required": ["path", "purpose"], "properties": {
            "path": {"type": "string"}, "purpose": {"type": "string", "description": "what this file contains, specific enough to write it"}}},
            "description": "in writing order: structure first (index.html / server), then styles, then scripts, README last"},
        "install": {"type": "array", "items": {"type": "string"}, "description": "install commands, e.g. ['npm install']; empty for static"},
        "start": {"type": "string", "description": "start command, e.g. 'npm start' or 'python app.py'; empty for static"}}}}
WRITE_TOOL = {"name": "write_file", "description": "Write one complete file.", "input_schema": {
    "type": "object", "required": ["path", "content"], "properties": {"path": {"type": "string"}, "content": {"type": "string"}}}}
CHANGE_TOOL = {"name": "apply_changes", "description": "Apply the requested change to the project.", "input_schema": {
    "type": "object", "required": ["summary", "files"], "properties": {
        "summary": {"type": "string", "description": "one or two sentences describing what changed, for the user"},
        "files": {"type": "array", "items": {"type": "object", "required": ["path", "content"], "properties": {
            "path": {"type": "string"}, "content": {"type": "string", "description": "the COMPLETE new file content"}}},
            "description": "only files that change or are new, each with its full content"},
        "delete": {"type": "array", "items": {"type": "string"}}}}}


# ---------- validation and storage ----------
def check_path(raw):
    p = str(raw).replace("\\", "/").strip()
    if p.startswith("/") or re.match(r"^[A-Za-z]:", p):
        raise ValueError(f"Bad path: {raw!r}. Use relative paths only.")
    parts = p.rstrip("/").split("/")
    if not p or len(p) > 200 or any(x in ("", ".", "..") for x in parts) or parts[0] in SKIP:
        raise ValueError(f"Bad path: {raw!r}.")
    return "/".join(parts)


def clean_files(fl):
    """Validate a generated file list. Raises ValueError with a message the model can act on."""
    if not isinstance(fl, list) or not fl or len(fl) > 80:
        raise ValueError("Provide between 1 and 80 files.")
    out, total = [], 0
    for f in fl:
        content = str(f.get("content", ""))
        total += len(content.encode())
        out.append({"path": check_path(f.get("path", "")), "content": content})
    if total > 1_500_000:
        raise ValueError("Project too large (limit 1.5 MB of text). Make it smaller.")
    return out


def slug(s):
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9-]", "-", str(s).lower())).strip("-")[:48] or "project"


def unique_dir(name):
    WORKSPACE.mkdir(parents=True, exist_ok=True)
    d, n = WORKSPACE / name, 2
    while d.exists():
        d, n = WORKSPACE / f"{name}-{n}", n + 1
    return d


def project_dir(name):
    n = str(name)
    d = (WORKSPACE / n).resolve()
    if not n or "/" in n or "\\" in n or n.startswith(".") or d.parent != WORKSPACE.resolve() or not d.is_dir():
        raise ValueError(f"No project named {name!r}.")
    return d


def write(d, path, content):
    t = (d / check_path(path)).resolve()
    if d.resolve() not in t.parents:
        raise ValueError("Path escapes the project folder.")
    t.parent.mkdir(parents=True, exist_ok=True)
    t.write_text(content, encoding="utf-8")


def walk(d):
    """Project files (relative paths), skipping dependency and build folders."""
    out = []
    for p in sorted(d.rglob("*")):
        rel = p.relative_to(d)
        if p.is_file() and not (set(rel.parts) & SKIP) and not any(x.startswith(".") and x not in (".gitignore", ".env.example") for x in rel.parts):
            out.append(rel.as_posix())
    return out


def is_text(path):
    p = path.lower()
    return any(p.endswith(e) for e in TEXT) or "." not in p.rsplit("/", 1)[-1]


def reg_load():
    try:
        return json.loads(REG.read_text()) if REG.exists() else {}
    except Exception:
        return {}


def reg_save(r):
    with L:
        REG.write_text(json.dumps(r, indent=1))


def reg_update(name, **k):
    with L:
        r = reg_load()
        r[name] = {**r.get(name, {"name": name, "created": time.time(), "version": 0}), **k, "updated": time.time()}
        reg_save(r)
        return r[name]


def detect_stack(d):
    if (d / "package.json").exists():
        return "node"
    if (d / "requirements.txt").exists() or (d / "app.py").exists():
        return "python"
    return "static"


def list_projects():
    if not WORKSPACE.exists():
        return []
    r, out = reg_load(), []
    for d in sorted((x for x in WORKSPACE.iterdir() if x.is_dir() and not x.name.startswith(".")), key=lambda x: -x.stat().st_mtime):
        m = r.get(d.name, {})
        st = m.get("stack") or detect_stack(d)
        out.append({"name": d.name, "title": m.get("title") or d.name, "summary": m.get("summary", ""), "stack": st,
                    "kind": m.get("kind", ""), "version": m.get("version", 0), "updated": m.get("updated") or d.stat().st_mtime,
                    "has_index": (d / "index.html").exists(), "install": m.get("install", []), "start": m.get("start", ""),
                    "history": m.get("history", [])[-12:]})
    return out


# ---------- versions ----------
def snapshot(name, note):
    d = WORKSPACE / name
    with L:
        m = reg_load().get(name, {})
        v = int(m.get("version", 0)) + 1
        dest = VERS / name / str(v)
        if dest.exists():
            shutil.rmtree(dest)
        for f in walk(d):
            (dest / f).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(d / f, dest / f)
        hist = (m.get("history", []) + [{"v": v, "note": note[:200], "t": time.time()}])[-40:]
        reg_update(name, version=v, history=hist)
        for old in sorted((int(x.name) for x in (VERS / name).iterdir() if x.name.isdigit()))[:-20]:
            shutil.rmtree(VERS / name / str(old), ignore_errors=True)
        return v


def undo(name):
    d = project_dir(name)
    with L:
        m = reg_load().get(name, {})
        v = int(m.get("version", 0))
        prev = VERS / name / str(v - 1)
        if v <= 1 or not prev.exists():
            raise ValueError("There's no earlier version to go back to.")
        for f in walk(d):
            (d / f).unlink()
        for f in walk(prev):
            (d / f).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(prev / f, d / f)
        shutil.rmtree(VERS / name / str(v), ignore_errors=True)
        reg_update(name, version=v - 1, history=[h for h in m.get("history", []) if h["v"] < v])
        return v - 1


# ---------- model calls ----------
def _call(system, messages, tool, max_tokens=None):
    with llm.client().messages.stream(model=llm.model("deep"), max_tokens=max_tokens or MAXTOK, system=system, tools=[tool],
                                      tool_choice={"type": "tool", "name": tool["name"]}, messages=messages) as s:
        msg = s.get_final_message()
    for b in msg.content:
        if b.type == "tool_use":
            if msg.stop_reason == "max_tokens":
                raise OverflowError("The output was cut off.")
            return b.input
    raise RuntimeError("The model didn't return the expected output.")


def _sys(extra):
    return [{"type": "text", "text": GUIDE}, {"type": "text", "text": extra, "cache_control": {"type": "ephemeral"}}]


def _context(d, budget=150_000, only=None):
    parts, used = [], 0
    for f in (only or walk(d)):
        p = d / f
        if not p.exists() or not is_text(f):
            parts.append(f"=== {f} (binary or missing, not shown)")
            continue
        txt = p.read_text(errors="ignore")
        if used + len(txt) > budget:
            parts.append(f"=== {f} ({len(txt)} chars, not shown: context full)")
            continue
        used += len(txt)
        parts.append(f"=== {f}\n{txt}")
    return "\n\n".join(parts)


# ---------- jobs ----------
def _job(kind, title, steps):
    jid = uuid.uuid4().hex[:10]
    JOBS[jid] = {"id": jid, "kind": kind, "status": "running", "title": title, "project": None, "steps": [{"label": s, "state": "pending"} for s in steps],
                 "files": [], "summary": "", "error": None, "started": time.time(), "version": None, "stack": None}
    return JOBS[jid]


def _step(j, i, state="active", label=None):
    while len(j["steps"]) <= i:
        j["steps"].append({"label": "", "state": "pending"})
    for k, s in enumerate(j["steps"]):
        if k < i and s["state"] in ("active", "pending"):
            s["state"] = "done"
    j["steps"][i]["state"] = state
    if label:
        j["steps"][i]["label"] = label


def get_job(jid):
    return JOBS.get(jid)


def start_build(prompt, kind="auto", style="auto", on_done=None):
    prompt = str(prompt).strip()[:6000]
    if len(prompt) < 4:
        raise ValueError("Describe what to build.")
    j = _job("build", prompt[:80], ["Planning the project"])
    threading.Thread(target=_build, args=(j, prompt, kind if kind in KINDS else "auto", style if style in STYLES else "auto", on_done), daemon=True).start()
    return j["id"]


def _build(j, prompt, kind, style, on_done):
    try:
        _step(j, 0)
        brief = f"REQUEST: {prompt}\nTYPE: {KINDS[kind]}\nVISUAL DIRECTION: {STYLES[style]}"
        plan = _call(_sys("Plan this project. Pick the simplest stack that fully delivers it."), [{"role": "user", "content": brief}], PLAN_TOOL, 8000)
        files = [{"path": check_path(f["path"]), "purpose": str(f.get("purpose", ""))} for f in plan["files"]][:25]
        if not files:
            raise ValueError("The plan had no files.")
        stack = plan["stack"] if plan.get("stack") in ("static", "node", "python") else "static"
        if stack == "static" and not any(f["path"] == "index.html" for f in files):
            files.insert(0, {"path": "index.html", "purpose": "the page"})
        d = unique_dir(slug(plan.get("name") or plan.get("title")))
        d.mkdir(parents=True)
        name = d.name
        j.update(project=name, title=plan.get("title") or name, stack=stack, summary=plan.get("summary", ""))
        reg_update(name, title=j["title"], summary=j["summary"], stack=stack, kind=kind, prompt=prompt, design=plan.get("design", ""),
                   install=[str(c) for c in plan.get("install", [])][:4] if stack != "static" else [], start=str(plan.get("start", "")) if stack != "static" else "")
        _step(j, 0, "done", f"Planned {len(files)} files ({stack})")
        shared = "PLAN:\n" + json.dumps({**plan, "files": files}, indent=1) + f"\n\n{brief}"
        for i, f in enumerate(files, start=1):
            _step(j, i, "active", f"Writing {f['path']}")
            ask = f"Files written so far:\n\n{_context(d, 90_000, only=j['files']) or '(none yet)'}\n\nNow write {f['path']}: {f['purpose']}\nIt must be complete and consistent with the plan and the files above."
            try:
                out = _call(_sys(shared), [{"role": "user", "content": ask}], WRITE_TOOL)
            except OverflowError:
                out = _call(_sys(shared), [{"role": "user", "content": ask + "\nYour previous attempt was too long: keep this file tighter while keeping it complete."}], WRITE_TOOL)
            write(d, f["path"], str(out.get("content", "")))
            j["files"].append(f["path"])
            _step(j, i, "done", f"Wrote {f['path']}")
        j["version"] = snapshot(name, "First build")
        j["steps"].append({"label": "Preview ready" if stack == "static" else "Ready to run", "state": "done"})
        j["status"] = "done"
    except Exception as e:
        log.exception("build failed")
        j.update(status="error", error=f"{type(e).__name__}: {e}" if not isinstance(e, ValueError) else str(e))
        for s in j["steps"]:
            if s["state"] == "active":
                s["state"] = "error"
    if on_done:
        try:
            on_done(j)
        except Exception:
            pass


def start_iterate(name, instruction, on_done=None):
    d = project_dir(name)
    instruction = str(instruction).strip()[:4000]
    if not instruction:
        raise ValueError("Say what to change.")
    j = _job("iterate", instruction[:80], ["Reading the project", "Making the change", "Saving a new version"])
    j.update(project=d.name, stack=reg_load().get(d.name, {}).get("stack") or detect_stack(d))
    threading.Thread(target=_iterate, args=(j, d, instruction, on_done), daemon=True).start()
    return j["id"]


def _iterate(j, d, instruction, on_done):
    try:
        _step(j, 0)
        m = reg_load().get(d.name, {})
        ctx = f"PROJECT: {m.get('title', d.name)}\nORIGINAL REQUEST: {m.get('prompt', '')}\nDESIGN NOTES: {m.get('design', '')}\n\nCURRENT FILES:\n\n" + _context(d)
        _step(j, 1)
        ask = f"Change request: {instruction}\n\nApply it with apply_changes. Return each changed or new file in full. Keep everything else working."
        try:
            out = _call(_sys(ctx), [{"role": "user", "content": ask}], CHANGE_TOOL)
        except OverflowError:
            out = _call(_sys(ctx), [{"role": "user", "content": ask + "\nYour previous attempt was too long: only return the files that must change."}], CHANGE_TOOL)
        fl = clean_files(out.get("files") or [])
        for f in fl:
            write(d, f["path"], f["content"])
        for p in out.get("delete") or []:
            t = (d / check_path(p)).resolve()
            if d.resolve() in t.parents and t.is_file():
                t.unlink()
        j["files"] = [f["path"] for f in fl]
        _step(j, 2)
        j["summary"] = str(out.get("summary", "Done."))[:600]
        j["version"] = snapshot(d.name, instruction)
        _step(j, 3, "done", f"Saved version {j['version']}")
        j["status"] = "done"
    except Exception as e:
        log.exception("change failed")
        j.update(status="error", error=f"{type(e).__name__}: {e}" if not isinstance(e, ValueError) else str(e))
        for s in j["steps"]:
            if s["state"] == "active":
                s["state"] = "error"
    if on_done:
        try:
            on_done(j)
        except Exception:
            pass


def zip_bytes(name):
    import io, zipfile
    d = project_dir(name)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for f in walk(d):
            z.write(d / f, f"{d.name}/{f}")
    return buf.getvalue()


def read_file(name, path):
    d = project_dir(name)
    t = (d / check_path(path)).resolve()
    if d.resolve() not in t.parents or not t.is_file():
        raise ValueError("No such file.")
    if not is_text(path) or t.stat().st_size > 400_000:
        return f"({t.stat().st_size} bytes, not shown)"
    return t.read_text(errors="ignore")
