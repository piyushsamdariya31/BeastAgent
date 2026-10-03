"""Image generation through a separate image service (default: OpenAI Images API). Needs IMAGE_API_KEY in .env."""
import base64, json, os, re, time, urllib.request
from pathlib import Path

SIZES = {"1024x1024", "1536x1024", "1024x1536"}


def generate(prompt, size="1024x1024"):
    key = os.getenv("IMAGE_API_KEY") or os.getenv("OPENAI_API_KEY")
    if not key:
        raise RuntimeError("Image generation isn't set up. Add IMAGE_API_KEY to .env (see README).")
    if size not in SIZES:
        size = "1024x1024"
    req = urllib.request.Request(os.getenv("IMAGE_BASE_URL", "https://api.openai.com/v1") + "/images/generations",
                                 data=json.dumps({"model": os.getenv("IMAGE_MODEL", "gpt-image-1"), "prompt": prompt[:4000], "size": size, "n": 1}).encode(),
                                 headers={"Authorization": "Bearer " + key, "Content-Type": "application/json"})
    r = json.load(urllib.request.urlopen(req, timeout=180))["data"][0]
    img = base64.b64decode(r["b64_json"]) if r.get("b64_json") else urllib.request.urlopen(r["url"], timeout=60).read()
    d = Path(os.getenv("BEAST_IMAGES", str(Path.home() / "BeastImages")))
    d.mkdir(parents=True, exist_ok=True)
    f = d / f"{re.sub(r'[^a-z0-9]+', '-', prompt.lower())[:40].strip('-') or 'image'}-{int(time.time())}.png"
    f.write_bytes(img)
    return str(f)
