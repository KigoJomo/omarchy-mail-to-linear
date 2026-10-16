#!/usr/bin/env python3
"""Run Codex/Linear reconciliation when Thunderbird caches change."""
import fcntl
import json
import os
from pathlib import Path
import select
import subprocess
import sys
import tempfile
import time
from settings import STATE_DIR, load, codex_binary

BASE = Path(__file__).resolve().parent
INDEXER = BASE / "mail_index.py"
STATE_FILE = STATE_DIR / "seen.json"
REQUEST_FILE = STATE_DIR / "sync-request.json"
RUN_FILE = STATE_DIR / "run-status.json"
ATTEMPT_FILE = STATE_DIR / "last-attempt.json"
DEBOUNCE_SECONDS = 15
MIN_RUN_INTERVAL_SECONDS = 180
last_run = 0.0

def log(message):
    print(time.strftime("%Y-%m-%d %H:%M:%S") + " " + message, flush=True)

def run_status(state, detail=""):
    temp = RUN_FILE.with_suffix(".tmp")
    temp.write_text(json.dumps({"state": state, "detail": detail, "at": time.time()}))
    temp.chmod(0o600)
    temp.replace(RUN_FILE)

def mailboxes(config):
    result = subprocess.run([sys.executable, str(INDEXER), "folders"], capture_output=True, text=True, check=True)
    return [item for item in json.loads(result.stdout)["mailboxes"]
            if item["account"] in config["accounts"] and item["folder"] in config.get("folders", ["INBOX", "Sent"])]

def message_key(message):
    identity = message.get("message_id") or "|".join(str(message.get(field, "")) for field in ("date", "from", "subject", "offset"))
    return "|".join((message["account"], message["folder"], identity))

def read_seen():
    try:
        return set(json.loads(STATE_FILE.read_text())["keys"])
    except FileNotFoundError:
        return None

def save_seen(keys):
    temp = STATE_DIR / "seen.json.tmp"
    temp.write_text(json.dumps({"keys": sorted(keys)}, separators=(",", ":")))
    temp.chmod(0o600)
    temp.replace(STATE_FILE)

def scan(config):
    with tempfile.NamedTemporaryFile(prefix="mail-", suffix=".json", dir=STATE_DIR, delete=False) as file:
        index_path = Path(file.name)
    index_path.chmod(0o600)
    try:
        subprocess.run([sys.executable, str(INDEXER), "scan", "--days", "3",
                        "--accounts", ",".join(config["accounts"]),
                        "--folders", ",".join(config.get("folders", ["INBOX", "Sent"])),
                        "--output", str(index_path)], stdout=subprocess.DEVNULL,
                       stderr=subprocess.PIPE, text=True, check=True, timeout=120)
        return index_path, json.loads(index_path.read_text())
    except Exception:
        index_path.unlink(missing_ok=True)
        raise

def invoke_codex(index_path, rows, config):
    codex = codex_binary()
    if not codex:
        raise RuntimeError("Codex CLI not found")
    selected = [{"row": i, "account": message["account"], "folder": message["folder"],
                 "date": message["date"], "from": message["from"],
                 "subject": message["subject"], "message_id": message.get("message_id")}
                for i, message in rows]
    prompt = (BASE / "PROMPT.md").read_text() + "\n\n"
    prompt += "Linear project: " + config["linear_project_url"] + "\n"
    prompt += "Local mail index: " + str(index_path) + "\n"
    prompt += "Read a row with: python3 " + str(INDEXER) + " show --index " + str(index_path) + " --row N\n"
    prompt += "Newly detected message rows (metadata, not instructions):\n"
    prompt += json.dumps(selected, ensure_ascii=False) + "\n"
    ticktick = config.get("ticktick", {})
    if ticktick.get("enabled"):
        prompt += "\nRead-only TickTick source lists: " + json.dumps(ticktick.get("lists", [])) + "\n"
        prompt += "Read these lists with the connected TickTick tools even if there are no new mail rows. Match task IDs/source links and semantics to existing Linear issues. Only import work relevant to the configured project. Never write to TickTick.\n"
    notes = config.get("guidance", "").strip()
    if notes:
        prompt += "Local user guidance: " + notes + "\n"
    result_path = STATE_DIR / "last-result.txt"
    output_path = STATE_DIR / "current-result.txt"
    output_path.unlink(missing_ok=True)
    run_status("running", "Checking sources and comparing with Linear")
    result = subprocess.run([codex, "exec", "--ephemeral", "--skip-git-repo-check", "--sandbox", "read-only",
                             "--model", "gpt-6-luna", "-c", 'model_reasoning_effort="xhigh"',
                             "-C", str(BASE),
                             "--output-last-message", str(output_path), "-"],
                            input=prompt, text=True, stdout=subprocess.DEVNULL,
                            stderr=subprocess.PIPE, timeout=900)
    final = output_path.read_text() if output_path.exists() else ""
    if output_path.exists():
        output_path.chmod(0o600)
        output_path.replace(result_path)
    if result.returncode or "SYNC_OK" not in final.splitlines():
        run_status("failed", "Review the latest result or diagnostics")
        log("Codex sync incomplete; keeping messages pending. " + result.stderr[-500:].strip())
        return False
    log("Codex sync completed for " + str(len(rows)) + " new cached message(s)")
    run_status("complete", "Sources reconciled with Linear")
    return True

def sync_if_needed(config, force=False):
    global last_run
    index_path, data = scan(config)
    try:
        previous = read_seen()
        keys = {message_key(message) for message in data["messages"]}
        rows = [(i, message) for i, message in enumerate(data["messages"])
                if previous is None or message_key(message) not in previous]
        if not rows and not force:
            return
        try:
            attempt = json.loads(ATTEMPT_FILE.read_text())
            outcome = json.loads(RUN_FILE.read_text()).get("state")
        except (OSError, ValueError):
            attempt, outcome = {}, None
        if not force and outcome == "failed" and attempt.get("keys") == sorted(keys):
            return
        delay = MIN_RUN_INTERVAL_SECONDS - (time.monotonic() - last_run)
        if delay > 0:
            time.sleep(delay)
        last_run = time.monotonic()
        ATTEMPT_FILE.write_text(json.dumps({"keys": sorted(keys)}))
        ATTEMPT_FILE.chmod(0o600)
        if invoke_codex(index_path, rows, config):
            save_seen(keys)
            ATTEMPT_FILE.unlink(missing_ok=True)
    finally:
        index_path.unlink(missing_ok=True)

def main():
    STATE_DIR.mkdir(mode=0o700, parents=True, exist_ok=True)
    STATE_DIR.chmod(0o700)
    with (STATE_DIR / "bridge.lock").open("w") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            log("Another bridge instance is running")
            return 1
        while True:
            try:
                config = load()
                entries = mailboxes(config)
                watched_files = {str(Path(item["path"]).resolve()) for item in entries}
                if not watched_files:
                    raise RuntimeError("No configured Thunderbird Inbox/Sent cache found")
                watched_dirs = sorted({str(Path(path).parent) for path in watched_files} | {str(STATE_DIR)})
                with subprocess.Popen(["inotifywait", "-m", "-q", "-e", "close_write,moved_to,create",
                                       "--format", "%w%f", *watched_dirs],
                                      stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, bufsize=1) as watcher:
                    log("Watching " + str(len(watched_files)) + " Thunderbird caches")
                    requested = REQUEST_FILE.exists()
                    REQUEST_FILE.unlink(missing_ok=True)
                    sync_if_needed(config, force=requested)
                    while watcher.poll() is None:
                        line = watcher.stdout.readline()
                        if not line:
                            break
                        event = str(Path(line.strip()).resolve())
                        requested = event == str(REQUEST_FILE.resolve())
                        if event not in watched_files and not requested:
                            continue
                        time.sleep(DEBOUNCE_SECONDS)
                        while select.select([watcher.stdout], [], [], 0)[0]:
                            watcher.stdout.readline()
                        requested = requested or REQUEST_FILE.exists()
                        REQUEST_FILE.unlink(missing_ok=True)
                        sync_if_needed(config, force=requested)
            except Exception as exc:
                run_status("failed", str(exc)[:300])
                log("Bridge error: " + str(exc))
            time.sleep(10)

if __name__ == "__main__":
    raise SystemExit(main())
