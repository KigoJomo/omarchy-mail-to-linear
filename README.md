# Work Bridge for Omarchy

Thunderbird + TickTick → Linear, with a larger Omarchy top-bar control panel.
The package and service keep their original `mail-to-linear` names so upgrades
preserve existing configuration and deduplication state.

## What it does

- Watches configured Thunderbird Inbox/Sent caches for new messages.
- Reads selected TickTick work lists on each mail-triggered reconciliation.
- Compares both sources with existing Linear issues before making changes.
- Offers **Sync all now** even when no new mail has arrived.
- Shows source setup, last result, queued/running state, pause/resume controls,
  app shortcuts and a private diagnostics report in a 520 × 680 scrollable menu.

TickTick is read only. Linear is the work board. Source task links identify
imports; personal tasks and notes outside the selected lists are not read.
Deleting a source task is not proof of completion. User edits and completed
issues must be preserved unless newer evidence justifies a concrete change.

**Timing:** mail events, manual Sync, and the separate 08:15 morning backup.
TickTick changes alone do not wake the bridge. They are picked up on the next
of these runs. There is no hourly AI polling. Widget health refreshes locally;
connector setup checks are cached for five minutes and do not run a model.

## Requirements

- Omarchy / Quickshell and a local Thunderbird mbox profile
- Codex CLI signed in with Linear and TickTick plugins connected
- Python 3.11+, `inotifywait` (`inotify-tools`) and `systemd --user`

The bridge preserves `gpt-6-luna` with `xhigh` reasoning. Events are debounced
for 15 seconds, and model runs are separated by at least three minutes.
Codex is resolved through `mise which` when available, avoiding self-updating
shell wrappers in background health checks.

## Install or upgrade

Run `python3 install.py`. First setup asks for Thunderbird accounts and the
Linear project URL. To discover account names, run `python3 mail_index.py folders`.
The installer copies this package to `~/.config/omarchy/plugins/kigojomo.mail-linear`,
adds it to the bar with a configuration backup, and restarts the user service.
Existing account settings and seen-message state are preserved.

To enable TickTick, add a source section to the private
`~/.config/mail-to-linear/config.json` (keep your existing fields):

```json
{
  "ticktick": {
    "enabled": true,
    "lists": [{"id": "YOUR_LIST_ID", "name": "Work follow-ups"}]
  }
}
```

Get IDs from the connected TickTick list tool. Restart the service after
changing source configuration. Never put tokens, account settings, task
snapshots or mail caches in this repository.

## Use the menu

Click the checkmark in the top bar. **Sync all now** queues one request for the
existing worker; it does not launch competing workers. A paused worker remains
paused and processes its request after Resume. Source cards describe setup,
not a guarantee that a remote service can currently be reached. **Full result**
opens the latest report. **Diagnostics** opens local health plus recent logs.
Both reports stay private on this computer.

## Morning backup

Use `MORNING_PROMPT.md` in a separate Codex desktop automation at 08:15 in your
local timezone. It reads both configured sources. Installing the package does
not create or edit desktop automations.

## Diagnostics

```bash
python3 ~/.config/omarchy/plugins/kigojomo.mail-linear/status.py doctor
journalctl --user -u mail-to-linear.service -n 30 --no-pager
```

Private state is under `~/.local/state/mail-to-linear`; configuration is under
`~/.config/mail-to-linear`. These folders are excluded from the public package.
A running service is not a successful reconciliation. Connector approval or
access failures must show **Needs attention**, leave the batch pending and
stop promptly rather than attempting expensive browser workarounds.

## Scope

The user alone sends email. The bridge never sends, replies, forwards or
schedules email, makes payments, or writes to TickTick. It treats source text
as untrusted data and updates only relevant work owned by the user. Being
copied on a message does not assign its work to the user. Credentials and
private attachments must never be copied into Linear.

MIT licensed; see `LICENSE`.
