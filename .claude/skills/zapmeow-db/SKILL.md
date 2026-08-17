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
(a SQLite/GORM + whatsmeow schema). This DB is **live** — the zapmeow
service may be writing to it. Always query read-only and keep queries
short-lived:

```bash
sqlite3 -readonly -header -column ~/.zapmeow/zapmeow.db "SELECT ...;"
```

Never run `UPDATE`/`DELETE`/`DROP`/schema changes against this file. A
`zapmeow.db.old` backup also exists alongside it if ever needed for
comparison.

## Key tables

- **`messages`** — every message. `sender_jid`, `chat_jid` (bare number, no
  `@s.whatsapp.net`/`@g.us` suffix), `timestamp`, `body`, `media_type`,
  `from_me` (1 = sent by the account owner), `instance_id`.
- **`groups`** — `j_id` (`<id>@g.us`), `group_name`/`name`, `owner_j_id`,
  `participants` (JSON).
- **`whatsmeow_contacts`** — `our_jid`, `their_jid` (`<number>@s.whatsapp.net`),
  `first_name`, `full_name`, `push_name`, `business_name`. **Has one row per
  `(our_jid, their_jid)` pair** — since several device instances are paired
  under this account, the same `their_jid` repeats 3x. Always dedupe by
  `their_jid` before joining (see below) or you'll get fan-out duplicate
  rows.
- **`whatsmeow_lid_map`** — maps newer opaque `lid` identifiers (which is
  what many `chat_jid`/`sender_jid` values actually are) to the real phone
  number in `pn`. **Needed for most name lookups** — see below.
- **`accounts`** — paired WhatsApp instances/devices; `user` (phone number),
  `status` (e.g. `CONNECTED`, `TIMEOUT`, `UNPAIRED`), `instance_id`.
- **`transcriptions`** — audio transcriptions, keyed by `message_id`.
- **`chat_summary_jobs`** — configured chat/group summary jobs.

## Resolving a `chat_jid`/`sender_jid` to a human name

`chat_jid` and `sender_jid` in `messages` are bare IDs with no domain
suffix, and are frequently the newer `lid` form rather than a phone number.
Resolve a name by trying, in order: group name → direct contact match →
contact match via the lid→phone map. Start every query with a **deduped
contacts CTE** (`whatsmeow_contacts` has 3 rows per `their_jid`, one per
paired device — joining the raw table causes duplicate result rows):

```sql
WITH c AS (
  SELECT their_jid, MAX(full_name) AS full_name, MAX(push_name) AS push_name
  FROM whatsmeow_contacts GROUP BY their_jid
)
```

then join like this (adjust the alias `m.chat_jid` / `m.sender_jid` as
needed):

```sql
LEFT JOIN groups g   ON g.j_id = <jid> || '@g.us'
LEFT JOIN c c1        ON c1.their_jid = <jid> || '@s.whatsapp.net'
LEFT JOIN whatsmeow_lid_map lm ON lm.lid = <jid>
LEFT JOIN c c2        ON c2.their_jid = lm.pn || '@s.whatsapp.net'
-- resolved name:
COALESCE(g.group_name, g.name, c1.full_name, c1.push_name,
         c2.full_name, c2.push_name, <jid>) AS name
```

`chat_jid = '0'` shows up for a handful of system/status rows — safe to
ignore or filter with `WHERE chat_jid != '0'`.

## Example queries

### Recent messages (most recent first, across all chats)

```bash
sqlite3 -readonly -header -column ~/.zapmeow/zapmeow.db "
WITH c AS (
  SELECT their_jid, MAX(full_name) AS full_name, MAX(push_name) AS push_name
  FROM whatsmeow_contacts GROUP BY their_jid
)
SELECT m.timestamp,
       COALESCE(g.group_name, g.name, c1.full_name, c1.push_name, c2.full_name, c2.push_name, m.chat_jid) AS chat,
       CASE WHEN m.from_me = 1 THEN 'me'
            ELSE COALESCE(cs1.full_name, cs1.push_name, cs2.full_name, cs2.push_name, m.sender_jid) END AS sender,
       substr(m.body, 1, 80) AS body
FROM messages m
LEFT JOIN groups g   ON g.j_id = m.chat_jid || '@g.us'
LEFT JOIN c c1        ON c1.their_jid = m.chat_jid || '@s.whatsapp.net'
LEFT JOIN whatsmeow_lid_map lm  ON lm.lid = m.chat_jid
LEFT JOIN c c2        ON c2.their_jid = lm.pn || '@s.whatsapp.net'
LEFT JOIN c cs1       ON cs1.their_jid = m.sender_jid || '@s.whatsapp.net'
LEFT JOIN whatsmeow_lid_map slm ON slm.lid = m.sender_jid
LEFT JOIN c cs2       ON cs2.their_jid = slm.pn || '@s.whatsapp.net'
ORDER BY m.timestamp DESC
LIMIT 20;
"
```

### Messages from a specific person (by name, case-insensitive)

```bash
sqlite3 -readonly -header -column ~/.zapmeow/zapmeow.db "
WITH c AS (
  SELECT their_jid, MAX(full_name) AS full_name, MAX(push_name) AS push_name
  FROM whatsmeow_contacts GROUP BY their_jid
)
SELECT m.timestamp, substr(m.body, 1, 100) AS body
FROM messages m
LEFT JOIN c c1 ON c1.their_jid = m.sender_jid || '@s.whatsapp.net'
LEFT JOIN whatsmeow_lid_map lm  ON lm.lid = m.sender_jid
LEFT JOIN c c2 ON c2.their_jid = lm.pn || '@s.whatsapp.net'
WHERE COALESCE(c1.full_name, c1.push_name, c2.full_name, c2.push_name, '') LIKE '%NAME%'
ORDER BY m.timestamp DESC
LIMIT 20;
"
```

### Full-text search across message bodies

```bash
sqlite3 -readonly -header -column ~/.zapmeow/zapmeow.db "
SELECT timestamp, chat_jid, sender_jid, substr(body,1,100)
FROM messages
WHERE body LIKE '%SEARCH TERM%'
ORDER BY timestamp DESC
LIMIT 30;
"
```

### List contacts

```bash
sqlite3 -readonly -header -column ~/.zapmeow/zapmeow.db "
SELECT their_jid, COALESCE(MAX(full_name), MAX(push_name), MAX(first_name)) AS name
FROM whatsmeow_contacts
GROUP BY their_jid
HAVING name IS NOT NULL
ORDER BY name;
"
```

### List groups (with participant count)

```bash
sqlite3 -readonly -header -column ~/.zapmeow/zapmeow.db "
SELECT j_id, COALESCE(group_name, name) AS name, owner_j_id,
       json_array_length(participants) AS n_participants
FROM groups
ORDER BY name;
"
```

### Most active chats (message counts, last 30 days)

```bash
sqlite3 -readonly -header -column ~/.zapmeow/zapmeow.db "
WITH c AS (
  SELECT their_jid, MAX(full_name) AS full_name, MAX(push_name) AS push_name
  FROM whatsmeow_contacts GROUP BY their_jid
)
SELECT COALESCE(g.group_name, g.name, c1.full_name, c1.push_name, c2.full_name, c2.push_name, m.chat_jid) AS chat,
       COUNT(*) AS n,
       MAX(m.timestamp) AS last_message
FROM messages m
LEFT JOIN groups g   ON g.j_id = m.chat_jid || '@g.us'
LEFT JOIN c c1        ON c1.their_jid = m.chat_jid || '@s.whatsapp.net'
LEFT JOIN whatsmeow_lid_map lm  ON lm.lid = m.chat_jid
LEFT JOIN c c2        ON c2.their_jid = lm.pn || '@s.whatsapp.net'
WHERE m.timestamp >= datetime('now', '-30 days')
GROUP BY chat
ORDER BY n DESC;
"
```

### Account/instance status

```bash
sqlite3 -readonly -header -column ~/.zapmeow/zapmeow.db "
SELECT id, instance_id, user, status FROM accounts WHERE status IS NOT NULL AND status != '';
"
```

## Notes

- `timestamp` is stored as ISO8601 with a UTC offset (e.g.
  `2026-04-21 07:33:29+01:00`) — works directly with SQLite's `datetime()`
  and string comparisons/ordering.
- `media_type = '1'` appears to flag media-bearing messages generically;
  `body` for those may be empty or contain a caption — there's no separate
  filename column, media files live under `STORAGE_PATH` (see
  `storage/` in `~/.zapmeow`), referenced by `media_path`.
- For voice-note text, join `transcriptions` on `message_id`.
