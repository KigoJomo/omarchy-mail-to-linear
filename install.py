#!/usr/bin/env python3
"""Install Mail to Linear as an Omarchy widget and systemd user service."""

from datetime import datetime
import json
from pathlib import Path
import shutil
import subprocess

from settings import CONFIG_DIR, CONFIG_FILE, SERVICE

ROOT = Path(__file__).resolve().parent
HOME = Path.home()
TARGET = HOME / ".config/omarchy/plugins/kigojomo.mail-linear"
SHELL = HOME / ".config/omarchy/shell.json"
UNIT = HOME / ".config/systemd/user" / SERVICE
FILES = ("manifest.json", "Widget.qml", "status.py", "settings.py", "mail_index.py",
         "bridge.py", "PROMPT.md", "MORNING_PROMPT.md", "install.py", "README.md", "LICENSE")


def configure():
    if CONFIG_FILE.exists():
        return
    print("Mail to Linear first-time setup")
    print("Accounts must match the names shown by: python3 mail_index.py folders")
    accounts = [item.strip() for item in input("Thunderbird accounts (comma separated): ").split(",") if item.strip()]
    project = input("Linear project URL: ").strip()
    if not accounts or not project.startswith("https://linear.app/"):
        raise SystemExit("At least one account and a Linear project URL are required")
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_DIR.chmod(0o700)
    CONFIG_FILE.write_text(json.dumps({"accounts": accounts, "folders": ["INBOX", "Sent"],
                                       "linear_project_url": project, "guidance": ""}, indent=2) + "\n")
    CONFIG_FILE.chmod(0o600)


def main():
    configure()
    codex_path = shutil.which("codex")
    if not codex_path:
        raise SystemExit("Codex CLI not found on PATH. Install Codex before setting up Mail to Linear.")
    service_path = f"{Path(codex_path).parent}:/usr/local/bin:/usr/bin"
    TARGET.mkdir(parents=True, exist_ok=True)
    for name in FILES:
        source, target = ROOT / name, TARGET / name
        if source.resolve() != target.resolve():
            shutil.copy2(source, target)

    config = json.loads(SHELL.read_text())
    right = config["bar"]["layout"]["right"]
    if not any(item.get("id") == "kigojomo.mail-linear" for item in right):
        insertion = next((i + 1 for i, item in enumerate(right) if item.get("id") == "omarchy.agents"), len(right))
        right.insert(insertion, {"id": "kigojomo.mail-linear"})
        backup = SHELL.with_name("shell.json.before-mail-linear-" + datetime.now().strftime("%Y%m%d-%H%M%S"))
        shutil.copy2(SHELL, backup)
        SHELL.write_text(json.dumps(config, indent=2) + "\n")
        print("Bar backup:", backup)

    UNIT.parent.mkdir(parents=True, exist_ok=True)
    UNIT.write_text(f"""[Unit]
Description=Update Linear from local Thunderbird cache changes using Codex
After=default.target

[Service]
Type=simple
Environment=PATH={service_path}
WorkingDirectory={TARGET}
ExecStart=/usr/bin/python3 {TARGET / 'bridge.py'}
Restart=always
RestartSec=10

[Install]
WantedBy=default.target
""")
    subprocess.run(["omarchy", "plugin", "validate", str(TARGET)], check=True)
    subprocess.run(["systemctl", "--user", "daemon-reload"], check=True)
    subprocess.run(["systemctl", "--user", "enable", "--now", SERVICE], check=True)
    subprocess.run(["systemctl", "--user", "restart", SERVICE], check=True)
    print("Installed Mail to Linear. Open the envelope in the top bar.")


if __name__ == "__main__":
    main()
