#!/usr/bin/env python3
"""Read-only Thunderbird mbox index. Message bodies stay in the local cache."""

import argparse
import configparser
from datetime import datetime, timedelta, timezone
from email import policy
from email.parser import BytesHeaderParser, BytesParser
from email.utils import parsedate_to_datetime
import html
import json
import mmap
from pathlib import Path
import re


def profile():
    for root in (Path.home() / ".thunderbird", Path.home() / ".config/thunderbird"):
        ini = root / "profiles.ini"
        if not ini.exists():
            continue
        data = configparser.ConfigParser()
        data.read(ini)
        sections = [name for name in data.sections() if name.startswith("Profile")]
        installed = next((data.get(name, "Default") for name in data.sections()
                          if name.startswith("Install") and data.has_option(name, "Default")), None)
        chosen = next((name for name in sections if data.get(name, "Path", fallback="") == installed), None)
        if chosen is None:
            chosen = next((name for name in sections if data.get(name, "Default", fallback="0") == "1"), None)
        if chosen is None and sections:
            chosen = sections[0]
        if chosen:
            candidate = Path(data.get(chosen, "Path"))
            if data.get(chosen, "IsRelative", fallback="1") == "1":
                candidate = root / candidate
            candidate = candidate.resolve()
            if (candidate / "prefs.js").exists():
                return candidate
    raise RuntimeError("No Thunderbird profile found")


def folders():
    base = profile()
    prefs = (base / "prefs.js").read_text(errors="replace")
    servers = {}
    for match in re.finditer(r'^user_pref\("mail\.server\.(server\d+)\.(directory|name)", (".*")\);$', prefs, re.M):
        servers.setdefault(match[1], {})[match[2]] = json.loads(match[3])
    for server in servers.values():
        directory = Path(server.get("directory", ""))
        if not directory.is_dir():
            continue
        account = server.get("name", directory.name)
        for path in directory.rglob("*"):
            if path.is_file() and not path.suffix:
                folder = "/".join(part.removesuffix(".sbd") for part in path.relative_to(directory).parts)
                yield {"account": account, "folder": folder, "path": str(path.resolve()),
                       "last_cache_modified": datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat()}


def index(days, accounts, wanted_folders):
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    rows, mailboxes = [], []
    for box in folders():
        if box["account"] not in accounts or box["folder"] not in wanted_folders:
            continue
        path = Path(box["path"])
        stat = path.stat()
        count = 0
        if stat.st_size:
            with path.open("rb") as file, mmap.mmap(file.fileno(), 0, access=mmap.ACCESS_READ) as data:
                starts = [0]
                at = 0
                while True:
                    at = data.find(b"\nFrom - ", at)
                    if at < 0:
                        break
                    starts.append(at + 1)
                    at += 8
                starts.append(len(data))
                for start, end in zip(starts, starts[1:]):
                    count += 1
                    boundary = data.find(b"\n\n", start, min(end, start + 100000))
                    if boundary < 0:
                        boundary = data.find(b"\r\n\r\n", start, min(end, start + 100000))
                    if boundary < 0:
                        continue
                    header = bytes(data[start:boundary]).split(b"\n", 1)[-1]
                    msg = BytesHeaderParser(policy=policy.default).parsebytes(header)
                    try:
                        date = parsedate_to_datetime(str(msg.get("Date", "")))
                        if date.tzinfo is None:
                            date = date.replace(tzinfo=timezone.utc)
                        if date.astimezone(timezone.utc) < cutoff:
                            continue
                    except (TypeError, ValueError, IndexError):
                        continue
                    try:
                        if int(str(msg.get("X-Mozilla-Status", "0000")), 16) & 0x0008:
                            continue
                    except ValueError:
                        pass
                    rows.append({"account": box["account"], "folder": box["folder"],
                                 "date": date.isoformat(), "from": str(msg.get("From", "")),
                                 "to": str(msg.get("To", "")), "subject": str(msg.get("Subject", "")),
                                 "message_id": str(msg.get("Message-ID", "")),
                                 "path": str(path), "offset": start, "length": end - start,
                                 "source_size": stat.st_size, "source_mtime_ns": stat.st_mtime_ns})
        mailboxes.append({**box, "cached_messages": count})
    rows.sort(key=lambda row: row["date"], reverse=True)
    return {"generated_at": datetime.now(timezone.utc).isoformat(), "days": days,
            "mailboxes": mailboxes, "messages": rows}


def show(index_file, row_number, max_chars):
    row = json.loads(index_file.read_text())["messages"][row_number]
    path = Path(row["path"])
    stat = path.stat()
    if stat.st_size != row["source_size"] or stat.st_mtime_ns != row["source_mtime_ns"]:
        raise RuntimeError("Mailbox changed; create a fresh index")
    with path.open("rb") as file:
        file.seek(row["offset"])
        raw = file.read(min(row["length"], 20_000_000)).split(b"\n", 1)[-1]
    message = BytesParser(policy=policy.default).parsebytes(raw)
    plain, rich, attachments = [], [], []
    for part in message.walk():
        if part.get_filename():
            attachments.append(str(part.get_filename()))
        elif part.get_content_type() == "text/plain":
            plain.append(part.get_content())
        elif part.get_content_type() == "text/html":
            rich.append(part.get_content())
    body = "\n".join(plain)
    if not body:
        body = html.unescape(re.sub(r"<[^>]+>", " ", "\n".join(rich)))
    return {"metadata": row, "body": body[:max_chars],
            "body_truncated": len(body) > max_chars, "attachments": attachments}


def main():
    parser = argparse.ArgumentParser()
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("folders")
    scan = commands.add_parser("scan")
    scan.add_argument("--days", type=int, default=3)
    scan.add_argument("--accounts", required=True)
    scan.add_argument("--folders", default="INBOX,Sent")
    scan.add_argument("--output", type=Path, required=True)
    detail = commands.add_parser("show")
    detail.add_argument("--index", type=Path, required=True)
    detail.add_argument("--row", type=int, required=True)
    detail.add_argument("--max-chars", type=int, default=12000)
    args = parser.parse_args()
    if args.command == "folders":
        print(json.dumps({"mailboxes": list(folders())}))
    elif args.command == "scan":
        result = index(args.days, args.accounts.split(","), args.folders.split(","))
        args.output.write_text(json.dumps(result))
        args.output.chmod(0o600)
        print(json.dumps({"messages": len(result["messages"])}))
    else:
        print(json.dumps(show(args.index, args.row, args.max_chars)))


if __name__ == "__main__":
    main()
