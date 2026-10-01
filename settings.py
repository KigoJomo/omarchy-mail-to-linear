"""Paths and local, untracked configuration for Mail to Linear."""

import json
from pathlib import Path

CONFIG_DIR = Path.home() / ".config/mail-to-linear"
CONFIG_FILE = CONFIG_DIR / "config.json"
STATE_DIR = Path.home() / ".local/state/mail-to-linear"
SERVICE = "mail-to-linear.service"


def load():
    config = json.loads(CONFIG_FILE.read_text())
    accounts = config.get("accounts", [])
    project = config.get("linear_project_url", "")
    if not isinstance(accounts, list) or not accounts or not all(isinstance(item, str) and item for item in accounts):
        raise ValueError("Set at least one Thunderbird account in " + str(CONFIG_FILE))
    if not project.startswith("https://linear.app/"):
        raise ValueError("Set a Linear project URL in " + str(CONFIG_FILE))
    return config
