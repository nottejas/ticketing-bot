#!/bin/bash
cd "$(dirname "$0")"
while true; do
    echo "[$(date)] Starting ticketing bot..."
    python -m src.main
    echo "[$(date)] Bot exited. Restarting in 10 seconds..."
    sleep 10
done
