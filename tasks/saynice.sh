#!/bin/bash
source ~/.zshrc
set -e

data=$( echo "select timestamp, sender_jid, body from messages WHERE timestamp >= datetime('now', '-7 days') and (chat_jid ='447709487896' )" |sqlite3 /home/james/.zapmeow/zapmeow.db | tr '\n' '¬' )

data2=$( echo $data|sed 's/447709487896/Steph/g' |sed 's/447906616842/James/g' )



ollama run Saynice < /tmp/data.txt  > /tmp/help.txt


text=$(cat /tmp/help.txt)

echo $text

curl -X 'POST' \
  'http://localhost:8900/api/1/chat/send/text' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d "$(jq -n --arg phone "447906616842" --arg text "$text" '{phone: $phone, text: $text}')"
