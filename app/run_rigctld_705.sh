#!/bin/bash

DEVICE="/dev/serial/by-id/usb-Icom_Inc._IC-705_IC-705_16001096-if00"
PORT="4532"
SPEED="115200"  # Use 4800 if your rig requires it
MODELS=(3085)

if pgrep -x "rigctld" > /dev/null; then
    echo "rigctld is already running"
    exit 0
fi

for MODEL in "${MODELS[@]}"; do
    echo "Trying rig model: $MODEL"
    rigctld -m "$MODEL" -r "$DEVICE" -s "$SPEED" -t "$PORT" \
        --set-conf=rts_state=OFF,dtr_state=OFF &
    
    sleep 2  # Give it time to start

    if ss -ltn | grep -q ":$PORT"; then
        echo "rigctld started successfully with model $MODEL"
        exit 0
    else
        echo "Failed with model $MODEL, trying next..."
        pkill -f "rigctld.*-m $MODEL"
    fi
done

echo "Failed to start rigctld with all provided models."

