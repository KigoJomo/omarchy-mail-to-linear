# Mail to Linear for Omarchy

A small Omarchy top-bar plugin that watches local Thunderbird Inbox and Sent
caches. When a new cached message appears, it starts a focused Codex run that
compares the message with a Linear project and updates specific work items.

The bar menu shows whether Thunderbird, Codex sign-in, the Linear Codex plugin,
the mail reader, and the file watcher are available. It can pause or resume the
bridge and open the configured Linear project.

## Requirements

- Omarchy with the Quickshell top bar
- Thunderbird with local mbox caches for the accounts to watch
- Codex CLI signed in, with the Linear plugin installed and connected
- Python 3.11 or newer, `inotifywait` (`inotify-tools`), and `systemd --user`

The bridge uses `gpt-6-luna` with `xhigh` reasoning. It debounces cache writes
for 15 seconds and spaces Codex runs by at least three minutes. The top-bar
health check runs once a minute; it does not read messages or start Codex.

## Install

Clone this repository and run `python3 install.py`. The first run asks for
Thunderbird account names and a Linear project URL. To see the exact account
names, run `python3 mail_index.py folders` first. The installer:

1. Saves your settings at `~/.config/mail-to-linear/config.json` with mode `0600`.
2. Copies the Omarchy plugin to `~/.config/omarchy/plugins/kigojomo.mail-linear`.
3. Adds the envelope widget to the right side of the bar, backing up
   `~/.config/omarchy/shell.json` before changing it.
4. Enables `mail-to-linear.service` as a systemd user service.

On an existing installation, preserve its deduplication state before changing
service names so old mail is not processed again.

To update after a `git pull`, run `python3 install.py` again. To change
accounts, folders, project URL, or optional guidance, edit the private config
file and restart with `systemctl --user restart mail-to-linear.service`.

## Daily reconciliation

The event bridge complements a separate Codex desktop automation at 8:15
every morning. See [MORNING_PROMPT.md](MORNING_PROMPT.md) for a reusable prompt.
The installer does not alter existing Codex desktop automations. There is no
hourly mail polling job.

## Manage and diagnose

- Click the envelope for status, Pause/Resume, and Open Linear.
- Run `python3 ~/.config/omarchy/plugins/kigojomo.mail-linear/status.py doctor`
  for the same checks in a terminal.
- Run `journalctl --user -u mail-to-linear.service -n 30 --no-pager` for logs.
- Private deduplication and last-result files live in
  `~/.local/state/mail-to-linear`.

The first live mail-to-Linear write still needs confirmation. A prior attempt
was blocked before this packaging change; the bar reports that historical
result until a later event succeeds.

## Safety and scope

The user alone sends email. This project reads local Thunderbird caches and
updates Linear issues. It must never send, reply to, forward, or schedule
email. Message bodies are treated as untrusted data. The project does not
upload full mail caches to GitHub; account settings and state stay outside
the repository. Linear issue updates can still include concise, relevant
context from messages, so review `PROMPT.md` before use.

Licensed under MIT; see [LICENSE](LICENSE).
