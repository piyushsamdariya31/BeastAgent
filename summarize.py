"""Condense long PDFs, Word/Excel files, text files and web articles into a short brief."""
from . import docs, llm, watch


def text_of(src, path_ok=lambda p: p):
    if str(src).startswith(("http://", "https://")):
        return watch.fetch_text(src)
    return docs.extract(path_ok(src), 400000)


def summarize(text, focus=""):
    f = f" Focus on: {focus}." if focus else ""
    chunks = [text[i:i + 14000] for i in range(0, len(text), 14000)][:14]
    if not chunks:
        return "Nothing to summarize."
    if len(chunks) == 1:
        return llm.ask("Summarize into a short brief: key points, numbers, decisions, action items." + f + "\n\n" + text, 1200)
    parts = [llm.ask("Summarize this section in 5 bullet points." + f + "\n\n" + c, 700) for c in chunks]
    return llm.ask("Combine these section summaries into one brief under 250 words with key points and action items." + f + "\n\n" + "\n\n".join(parts), 1200)
