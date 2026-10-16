"""Paths and local, untracked configuration for Mail to Linear."""

import json
import shutil
import subprocess
from pathlib import Path

CONFIG_DIR = Path.home() / ".config/mail-to-linear"
CONFIG_FILE = CONFIG_DIR / "config.json"
STATE_DIR = Path.home() / ".local/state/mail-to-linear"
SERVICE = "mail-to-linear.service"

def codex_binary():
    """Resolve mise without running the user's self-updating shell wrapper."""
    mise = shutil.which("mise")
    if mise:
        try:
            result = subprocess.run([mise, "which", "codex"], capture_output=True, text=True, timeout=3)
            path = result.stdout.strip()
            if result.returncode == 0 and Path(path).is_file():
                return path
        except (OSError, subprocess.TimeoutExpired):
            pass
    return shutil.which("codex")


def load():
    config = json.loads(CONFIG_FILE.read_text())
    accounts = config.get("accounts", [])
    project = config.get("linear_project_url", "")
    if not isinstance(accounts, list) or not accounts or not all(isinstance(item, str) and item for item in accounts):
        raise ValueError("Set at least one Thunderbird account in " + str(CONFIG_FILE))
    if not project.startswith("https://linear.app/"):
        raise ValueError("Set a Linear project URL in " + str(CONFIG_FILE))
    ticktick = config.get("ticktick", {})
    if not isinstance(ticktick, dict):
        raise ValueError("TickTick configuration must be an object")
    if ticktick.get("enabled"):
        lists = ticktick.get("lists", [])
        if not isinstance(lists, list) or not lists or not all(isinstance(item, dict) and isinstance(item.get("id"), str) and item["id"] for item in lists):
            raise ValueError("Choose at least one TickTick source list")
    return config
