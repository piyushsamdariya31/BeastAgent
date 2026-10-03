"""READ-ONLY file inspection. Only touches the path you pass in."""
from pathlib import Path
from . import docs, llm

TEXT_EXT = {".txt", ".md", ".py", ".js", ".ts", ".jsx", ".tsx", ".json", ".csv", ".html",
            ".css", ".java", ".c", ".cpp", ".cs", ".sql", ".yml", ".yaml", ".toml", ".ipynb"}
SKIP = {"node_modules", ".git", "__pycache__", "venv", ".venv", "dist", "build"}

def collect(path, max_files=40, max_chars=6000):
    p = Path(path).expanduser()
    files = [p] if p.is_file() else [f for f in p.rglob("*") if f.is_file()
             and f.suffix.lower() in TEXT_EXT | docs.DOC_EXT and not (set(f.parts) & SKIP)]
    if p.is_file():
        max_chars = max(max_chars, 40000)
    out = []
    for f in files[:max_files]:
        try:
            out.append(f"### {f}\n{docs.extract(f, max_chars) if f.suffix.lower() in docs.DOC_EXT else f.read_text(errors='ignore')[:max_chars]}")
        except Exception:
            pass
    return out, len(files)

def ask_about(path, question):
    chunks, total = collect(path)
    if not chunks:
        return "No readable text files found at that path."
    note = f"(showing {len(chunks)} of {total} files)\n" if total > len(chunks) else ""
    return note + llm.ask(f"{question}\n\nFILES:\n" + "\n\n".join(chunks), max_tokens=3000)
