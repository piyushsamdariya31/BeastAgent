"""Registers `python server.py` to run at every login/boot (Windows, macOS, Linux)."""
import sys, platform, subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PY = sys.executable
if platform.system() == "Windows":
    PY = PY.replace("python.exe", "pythonw.exe")  # no console window
CMD = f'"{PY}" "{ROOT / "server.py"}"'
os_name = platform.system()

if os_name == "Windows":
    subprocess.run(["schtasks", "/create", "/tn", "Beast", "/tr", CMD,
                    "/sc", "onlogon", "/f"], check=True)
elif os_name == "Darwin":
    plist = Path.home() / "Library/LaunchAgents/com.beast.plist"
    plist.write_text(f"""<?xml version="1.0" encoding="UTF-8"?>
<plist version="1.0"><dict><key>Label</key><string>com.beast</string>
<key>ProgramArguments</key><array><string>{PY}</string><string>{ROOT/'server.py'}</string></array>
<key>RunAtLoad</key><true/></dict></plist>""")
    subprocess.run(["launchctl", "load", str(plist)], check=True)
else:
    d = Path.home() / ".config/autostart"; d.mkdir(parents=True, exist_ok=True)
    (d / "beast.desktop").write_text(
        f"[Desktop Entry]\nType=Application\nName=Beast\nExec={CMD}\n")
print("Autostart installed.")
