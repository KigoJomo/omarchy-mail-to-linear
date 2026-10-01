#!/usr/bin/env python3
"""Local status and simple controls for the Mail to Linear bar widget."""

import json
from pathlib import Path
import shutil
import subprocess
import sys
from datetime import datetime
from settings import SERVICE, STATE_DIR, load



def run(args, timeout=10):
    try:
        return subprocess.run(args, capture_output=True, text=True, timeout=timeout)
    except (OSError, subprocess.TimeoutExpired):
        return None


def status():
    service = run(["systemctl", "--user", "is-active", SERVICE])
    service_state = service.stdout.strip() if service else "unavailable"
    codex = shutil.which("codex")
    login = run([codex, "login", "status"]) if codex else None
    plugins = run([codex, "plugin", "list", "--json"]) if codex else None
    try:
        linear = any(item.get("pluginId") == "linear@openai-curated-remote" and item.get("enabled")
                     for item in json.loads(plugins.stdout).get("installed", [])) if plugins and plugins.returncode == 0 else False
    except (ValueError, TypeError):
        linear = False
    thunderbird = run(["pgrep", "-x", "thunderbird"])
    cache = Path(__file__).resolve().parent / "mail_index.py"
    result = STATE_DIR / "last-result.txt"
    try:
        load()
        configured = True
    except (OSError, ValueError, KeyError):
        configured = False
    if result.exists():
        body = result.read_text(errors="replace")
        outcome = "Complete" if "SYNC_OK" in body.splitlines() else "Needs attention"
        updated = datetime.fromtimestamp(result.stat().st_mtime).strftime("%d %b %H:%M")
    else:
        outcome, updated = "Waiting for first sync", ""
    return {
        "bridge": service_state,
        "codex": bool(codex),
        "codexLogin": bool(login and login.returncode == 0),
        "thunderbird": bool(thunderbird and thunderbird.returncode == 0),
        "mailCache": cache.exists(),
        "configured": configured,
        "linear": linear,
        "inotify": bool(shutil.which("inotifywait")),
        "lastSync": outcome,
        "lastSyncAt": updated,
    }


def main():
    action = sys.argv[1] if len(sys.argv) > 1 else "status"
    if action == "status":
        print(json.dumps(status(), separators=(",", ":")))
    elif action in ("pause", "resume"):
        cmd = "stop" if action == "pause" else "start"
        completed = run(["systemctl", "--user", cmd, SERVICE])
        if not completed or completed.returncode:
            print((completed.stderr if completed else "systemctl unavailable").strip(), file=sys.stderr)
            return 1
    elif action == "open":
        subprocess.Popen(["xdg-open", load()["linear_project_url"]], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    elif action == "doctor":
        for key, value in status().items():
            print(f"{key}: {value}")
    else:
        print("Usage: status.py [status|pause|resume|open|doctor]", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
