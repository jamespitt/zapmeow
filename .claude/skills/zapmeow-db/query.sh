#!/usr/bin/env bash
#
# query.sh — read-only helper queries against the ZapMeow SQLite database.
#
# Usage: query.sh <command> [args...]
#
# Commands:
#   recent [N]              Most recent N messages across all chats (default 20)
#   chat <name> [N]         Most recent N messages in a chat/group matching <name> (default 20)
#   from <name> [N]         Most recent N messages sent by a contact matching <name> (default 20)
#   search <term> [N]       Messages whose body matches <term> (SQL LIKE, % wildcards ok; default 20)
#   contacts [name]         List contacts, optionally filtered by name
#   groups                  List groups with participant counts
#   active [days]           Most active chats in the last N days (default 30), with last message time
#   accounts                Paired WhatsApp account/instance status
#
# Env:
#   ZAPMEOW_DB   Path to the sqlite file (default: ~/.zapmeow/zapmeow.db)
#
# All queries are read-only (sqlite3 -readonly) against the live DB.

set -euo pipefail

DB="${ZAPMEOW_DB:-$HOME/.zapmeow/zapmeow.db}"

sql() {
  sqlite3 -readonly -header -column "$DB" "$1"
}

# Deduped contacts CTE, reused by every query that needs name resolution.
# whatsmeow_contacts has one row per (our_jid, their_jid) — since several
# device instances are paired, the same their_jid repeats 3x, so raw joins
# fan out into duplicate rows.
CONTACTS_CTE="
WITH c AS (
  SELECT their_jid, MAX(full_name) AS full_name, MAX(push_name) AS push_name
  FROM whatsmeow_contacts GROUP BY their_jid
)"

# Resolves a chat_jid to a human-readable name: group name -> direct contact
# match -> contact match via the lid->phone map.
CHAT_NAME_EXPR="COALESCE(g.group_name, g.name, c1.full_name, c1.push_name, c2.full_name, c2.push_name, m.chat_jid)"
CHAT_JOINS="
LEFT JOIN groups g              ON g.j_id = m.chat_jid || '@g.us'
LEFT JOIN c c1                  ON c1.their_jid = m.chat_jid || '@s.whatsapp.net'
LEFT JOIN whatsmeow_lid_map lm  ON lm.lid = m.chat_jid
LEFT JOIN c c2                  ON c2.their_jid = lm.pn || '@s.whatsapp.net'"

SENDER_NAME_EXPR="CASE WHEN m.from_me = 1 THEN 'me' ELSE COALESCE(cs1.full_name, cs1.push_name, cs2.full_name, cs2.push_name, m.sender_jid) END"
SENDER_JOINS="
LEFT JOIN c cs1                  ON cs1.their_jid = m.sender_jid || '@s.whatsapp.net'
LEFT JOIN whatsmeow_lid_map slm  ON slm.lid = m.sender_jid
LEFT JOIN c cs2                  ON cs2.their_jid = slm.pn || '@s.whatsapp.net'"

cmd_recent() {
  local n="${1:-20}"
  sql "
$CONTACTS_CTE
SELECT m.timestamp,
       $CHAT_NAME_EXPR AS chat,
       $SENDER_NAME_EXPR AS sender,
       substr(m.body, 1, 80) AS body
FROM messages m
$CHAT_JOINS
$SENDER_JOINS
ORDER BY m.timestamp DESC
LIMIT $n;
"
}

cmd_chat() {
  local name="${1:?usage: query.sh chat <name> [N]}"
  local n="${2:-20}"
  sql "
$CONTACTS_CTE
SELECT m.timestamp,
       $SENDER_NAME_EXPR AS sender,
       substr(m.body, 1, 100) AS body
FROM messages m
$CHAT_JOINS
$SENDER_JOINS
WHERE $CHAT_NAME_EXPR LIKE '%$name%'
ORDER BY m.timestamp DESC
LIMIT $n;
"
}

cmd_from() {
  local name="${1:?usage: query.sh from <name> [N]}"
  local n="${2:-20}"
  sql "
$CONTACTS_CTE
SELECT m.timestamp,
       $CHAT_NAME_EXPR AS chat,
       substr(m.body, 1, 100) AS body
FROM messages m
$CHAT_JOINS
$SENDER_JOINS
WHERE $SENDER_NAME_EXPR LIKE '%$name%'
ORDER BY m.timestamp DESC
LIMIT $n;
"
}

cmd_search() {
  local term="${1:?usage: query.sh search <term> [N]}"
  local n="${2:-20}"
  sql "
$CONTACTS_CTE
SELECT m.timestamp,
       $CHAT_NAME_EXPR AS chat,
       $SENDER_NAME_EXPR AS sender,
       substr(m.body, 1, 100) AS body
FROM messages m
$CHAT_JOINS
$SENDER_JOINS
WHERE m.body LIKE '%$term%'
ORDER BY m.timestamp DESC
LIMIT $n;
"
}

cmd_contacts() {
  local filter="${1:-}"
  sql "
SELECT their_jid, COALESCE(MAX(full_name), MAX(push_name), MAX(first_name)) AS name
FROM whatsmeow_contacts
GROUP BY their_jid
HAVING name IS NOT NULL ${filter:+AND name LIKE '%$filter%'}
ORDER BY name;
"
}

cmd_groups() {
  sql "
SELECT j_id, COALESCE(group_name, name) AS name, owner_j_id,
       json_array_length(participants) AS n_participants
FROM groups
ORDER BY name;
"
}

cmd_active() {
  local days="${1:-30}"
  sql "
$CONTACTS_CTE
SELECT $CHAT_NAME_EXPR AS chat,
       COUNT(*) AS n,
       MAX(m.timestamp) AS last_message
FROM messages m
$CHAT_JOINS
WHERE m.timestamp >= datetime('now', '-$days days')
GROUP BY chat
ORDER BY n DESC;
"
}

cmd_accounts() {
  sql "
SELECT id, instance_id, user, status
FROM accounts
WHERE status IS NOT NULL AND status != '';
"
}

main() {
  local command="${1:-}"
  [ $# -gt 0 ] && shift || true

  if [ ! -f "$DB" ]; then
    echo "Database not found: $DB" >&2
    exit 1
  fi

  case "$command" in
    recent)   cmd_recent "$@" ;;
    chat)     cmd_chat "$@" ;;
    from)     cmd_from "$@" ;;
    search)   cmd_search "$@" ;;
    contacts) cmd_contacts "$@" ;;
    groups)   cmd_groups "$@" ;;
    active)   cmd_active "$@" ;;
    accounts) cmd_accounts "$@" ;;
    *)
      sed -n '2,17p' "$0" | sed 's/^# \{0,1\}//'
      exit 1
      ;;
  esac
}

main "$@"
