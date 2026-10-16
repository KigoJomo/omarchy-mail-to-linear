#!/usr/bin/env python3
"""Read local health; queue reconciliation without starting competing workers."""
import json
from pathlib import Path
import subprocess
import sys
import time
from datetime import datetime
from settings import SERVICE, STATE_DIR, load, codex_binary


def run(args, timeout=8):
    try:
        return subprocess.run(args, capture_output=True, text=True, timeout=timeout)
    except (OSError, subprocess.TimeoutExpired):
        return None


def read_json(path, fallback):
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError):
        return fallback


def status():
    STATE_DIR.mkdir(mode=0o700, parents=True, exist_ok=True)
    config = {}
    try:
        config = load()
    except (OSError, ValueError, KeyError):
        pass
    service = run(["systemctl", "--user", "is-active", SERVICE])
    codex = codex_binary()
    health_file = STATE_DIR / "connector-health.json"
    connections = read_json(health_file, {})
    if time.time() - connections.get("checked", 0) > 300:
        login = run([codex, "login", "status"]) if codex else None
        plugins = run([codex, "plugin", "list", "--json"], timeout=20) if codex else None
        try:
            installed = json.loads(plugins.stdout).get("installed", []) if plugins and plugins.returncode == 0 else []
        except (ValueError, TypeError):
            installed = []
        connections = {"checked": time.time(), "codexLogin": bool(login and login.returncode == 0),
                       "linear": any(p.get("pluginId") == "linear@openai-curated-remote" and p.get("enabled") for p in installed)}
        health_file.write_text(json.dumps(connections))
        health_file.chmod(0o600)
    thunderbird = run(["pgrep", "-x", "thunderbird"])
    reader = Path(__file__).with_name("mail_index.py")
    folders = run([sys.executable, str(reader), "folders"])
    try:
        caches = [m for m in json.loads(folders.stdout)["mailboxes"]
                  if m["account"] in config.get("accounts", []) and m["folder"] in config.get("folders", ["INBOX", "Sent"])]
    except (AttributeError, ValueError, KeyError):
        caches = []
    result = STATE_DIR / "last-result.txt"
    body = result.read_text(errors="replace") if result.exists() else "No completed run yet."
    state = read_json(STATE_DIR / "run-status.json", {})
    outcome = "Syncing" if state.get("state") == "running" else "Needs attention" if state.get("state") == "failed" else "Complete" if "SYNC_OK" in body.splitlines() else "Needs attention" if result.exists() else "Waiting for first sync"
    ticktick = config.get("ticktick", {})
    return {"bridge": service.stdout.strip() if service else "unavailable", "codex": bool(codex),
            "codexLogin": connections.get("codexLogin", False), "linear": connections.get("linear", False),
            "thunderbird": bool(thunderbird and thunderbird.returncode == 0), "mailCache": bool(caches),
            "configured": bool(config), "ticktick": ticktick.get("enabled", False),
            "ticktickLists": ", ".join(item.get("name", item.get("id", "")) for item in ticktick.get("lists", [])),
            "cacheCount": len(caches), "mailboxes": [{"account": m["account"], "folder": m["folder"], "modified": m["last_cache_modified"]} for m in caches],
            "lastSync": outcome, "detail": state.get("detail", ""),
            "queued": (STATE_DIR / "sync-request.json").exists(),
            "lastSyncAt": datetime.fromtimestamp(result.stat().st_mtime).strftime("%d %b %H:%M") if result.exists() else "",
            "summary": "\n".join(line for line in body.splitlines() if line.strip() not in ("SYNC_OK", "SYNC_BLOCKED"))[:2200]}


def main():
    action = sys.argv[1] if len(sys.argv) > 1 else "status"
    if action in ("status", "doctor"):
        print(json.dumps(status(), indent=2 if action == "doctor" else None))
    elif action in ("pause", "resume"):
        result = run(["systemctl", "--user", "stop" if action == "pause" else "start", SERVICE])
        return 0 if result and result.returncode == 0 else 1
    elif action == "sync":
        STATE_DIR.mkdir(mode=0o700, parents=True, exist_ok=True)
        path = STATE_DIR / "sync-request.json"
        path.write_text(json.dumps({"requested_at": time.time()}))
        path.chmod(0o600)
        # A paused bridge stays paused; its queued request runs when resumed.
    elif action in ("open", "ticktick", "result", "diagnostics"):
        if action == "diagnostics":
            path = STATE_DIR / "diagnostics.txt"
            journal = run(["journalctl", "--user", "-u", SERVICE, "-n", "30", "--no-pager"])
            path.write_text(json.dumps(status(), indent=2) + "\n\n" + (journal.stdout if journal else "Logs unavailable"))
            path.chmod(0o600)
            target = str(path)
        elif action == "result":
            target = str(STATE_DIR / "last-result.txt")
        else:
            target = load()["linear_project_url"] if action == "open" else "https://ticktick.com/webapp/"
        subprocess.Popen(["xdg-open", target], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    else:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
