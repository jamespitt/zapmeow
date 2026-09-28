#!/bin/bash
set -e

INSTANCE_ID="${1:-3}"
BASE_URL="${ZAPMEOW_URL:-http://localhost:8900}"

echo "Checking ZapMeow instance $INSTANCE_ID on $BASE_URL..."

# Check command dependencies
if ! command -v qrencode &> /dev/null; then
    echo "Warning: 'qrencode' is not installed. You can install it via 'sudo apt install qrencode'."
    echo "Alternatively, open: $BASE_URL/api/$INSTANCE_ID/qrcode/page in your browser."
fi

# Trigger instance initialization and get initial status
STATUS=$(curl -s "$BASE_URL/api/$INSTANCE_ID/status" | grep -o '"status":"[^"]*"' | cut -d'"' -f4 || echo "UNKNOWN")

if [ "$STATUS" = "CONNECTED" ]; then
    echo "Instance $INSTANCE_ID is already CONNECTED!"
    exit 0
fi

echo "Instance $INSTANCE_ID is currently: $STATUS"
echo "Fetching QR code..."
echo "Or visit in your browser: $BASE_URL/api/$INSTANCE_ID/qrcode/page"
echo ""

LAST_CODE=""

while true; do
    STATUS_RESP=$(curl -s "$BASE_URL/api/$INSTANCE_ID/status" || echo "")
    STATUS=$(echo "$STATUS_RESP" | grep -o '"status":"[^"]*"' | cut -d'"' -f4 || echo "")

    if [ "$STATUS" = "CONNECTED" ]; then
        echo ""
        echo "=========================================="
        echo "🎉 WhatsApp Instance $INSTANCE_ID is CONNECTED!"
        echo "=========================================="
        exit 0
    elif [ "$STATUS" = "TIMEOUT" ]; then
        echo "Session timed out. Re-initiating connection..."
        curl -s "$BASE_URL/api/$INSTANCE_ID/qrcode" > /dev/null
        sleep 2
        continue
    fi

    QR_RESP=$(curl -s "$BASE_URL/api/$INSTANCE_ID/qrcode" || echo "")
    QR_CODE=$(echo "$QR_RESP" | grep -o '"qrcode":"[^"]*"' | cut -d'"' -f4 || echo "")

    if [ -n "$QR_CODE" ] && [ "$QR_CODE" != "$LAST_CODE" ]; then
        LAST_CODE="$QR_CODE"
        clear
        echo "========================================================"
        echo "  Scan this QR Code in WhatsApp (Linked Devices)       "
        echo "  Instance ID: $INSTANCE_ID                            "
        echo "  Browser URL: $BASE_URL/api/$INSTANCE_ID/qrcode/page  "
        echo "========================================================"
        echo ""
        if command -v qrencode &> /dev/null; then
            echo "$QR_CODE" | qrencode -t UTF8
        else
            echo "Raw code: $QR_CODE"
        fi
        echo ""
        echo "Waiting for scan (auto-refreshing)... Press Ctrl+C to stop."
    fi

    sleep 3
done
