---
name: zapmeow-db
description: >
  Query James's ZapMeow WhatsApp SQLite database at ~/.zapmeow/zapmeow.db —
  recent messages, message search, per-sender activity, list of contacts,
  list of groups and their members, and account/instance status. Use when
  asked about WhatsApp messages, chats, groups, contacts, or activity stored
  by ZapMeow. Triggers: "zapmeow db", "whatsapp messages", "who messaged me",
  "recent messages", "list groups", "list contacts", "chat history".
---

# ZapMeow SQLite Database

Read-only exploration of the ZapMeow database at `~/.zapmeow/zapmeow.db`
(a SQLite/GORM + whatsmeow schema). Use `query.sh` in this skill's
directory rather than writing raw SQL — it already handles the schema's
sharp edges (see below).

```bash
.claude/skills/zapmeow-db/query.sh <command> [args...]
```

| Command | Description |
|---|---|
| `recent [N]` | Most recent N messages across all chats (default 20) |
| `chat <name> [N]` | Most recent N messages in a chat/group matching `<name>` |
| `from <name> [N]` | Most recent N messages sent by a contact matching `<name>` |
| `search <term> [N]` | Messages whose body matches `<term>` (SQL `LIKE`, `%` wildcards ok) |
| `contacts [name]` | List contacts, optionally filtered by name |
| `groups` | List groups with participant counts |
| `active [days]` | Most active chats in the last N days (default 30) |
| `accounts` | Paired WhatsApp account/instance status |

Run it with no arguments to print this usage list. `<name>`/`<term>`
arguments are matched case-sensitively with SQL `LIKE`, so partial names
work (e.g. `from "James"`).

For anything not covered by a command, query the DB directly:

```bash
sqlite3 -readonly -header -column ~/.zapmeow/zapmeow.db "SELECT ...;"
```

This DB is **live** — the zapmeow service may be writing to it. Always
query read-only (`-readonly`) and never run `UPDATE`/`DELETE`/`DROP`/schema
changes against it. A `zapmeow.db.old` backup sits alongside it if ever
needed for comparison.

## Schema notes (for ad hoc queries)

- **`messages`** — every message. `sender_jid`, `chat_jid` (bare number, no
  `@s.whatsapp.net`/`@g.us` suffix), `timestamp`, `body`, `media_type`,
  `from_me` (1 = sent by the account owner), `instance_id`.
- **`groups`** — `j_id` (`<id>@g.us`), `group_name`/`name`, `owner_j_id`,
  `participants` (JSON).
- **`whatsmeow_contacts`** — `our_jid`, `their_jid` (`<number>@s.whatsapp.net`),
  `first_name`, `full_name`, `push_name`, `business_name`. **Has one row per
  `(our_jid, their_jid)` pair** — since several device instances are paired
  under this account, the same `their_jid` repeats 3x. Dedupe by `their_jid`
  before joining (`query.sh` already does this) or you'll get fan-out
  duplicate rows.
- **`whatsmeow_lid_map`** — maps newer opaque `lid` identifiers (which is
  what many `chat_jid`/`sender_jid` values actually are) to the real phone
  number in `pn`. Needed for most name lookups — resolve a name by trying,
  in order: group name → direct contact match → contact match via the
  lid→phone map (see `query.sh` for the exact join pattern).
- **`accounts`** — paired WhatsApp instances/devices; `user` (phone number),
  `status` (e.g. `CONNECTED`, `TIMEOUT`, `UNPAIRED`), `instance_id`.
- **`transcriptions`** — audio transcriptions, keyed by `message_id`.
- **`chat_summary_jobs`** — configured chat/group summary jobs.

`chat_jid = '0'` shows up for a handful of system/status rows — safe to
ignore or filter with `WHERE chat_jid != '0'`.

## Notes

- `timestamp` is stored as ISO8601 with a UTC offset (e.g.
  `2026-04-21 07:33:29+01:00`) — works directly with SQLite's `datetime()`
  and string comparisons/ordering.
- `media_type = '1'` appears to flag media-bearing messages generically;
  `body` for those may be empty or contain a caption — there's no separate
  filename column, media files live under `STORAGE_PATH` (see
  `storage/` in `~/.zapmeow`), referenced by `media_path`.
- For voice-note text, join `transcriptions` on `message_id`.
- Override the DB path with `ZAPMEOW_DB=/path/to/zapmeow.db query.sh ...`
  (e.g. to inspect `zapmeow.db.old`).
