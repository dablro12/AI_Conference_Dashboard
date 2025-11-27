#!/bin/bash

# Cloudflare Tunnel 중지 스크립트

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
PID_FILE="$PROJECT_DIR/.cloudflare_tunnel.pid"

if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    if ps -p "$PID" > /dev/null 2>&1; then
        echo "🛑 Stopping Cloudflare Tunnel (PID: $PID)..."
        kill "$PID" 2>/dev/null || true
        sleep 2
        if ps -p "$PID" > /dev/null 2>&1; then
            echo "⚠️  Process still running, force killing..."
            kill -9 "$PID" 2>/dev/null || true
        fi
        echo "✅ Cloudflare Tunnel stopped"
    else
        echo "⚠️  Process not found (PID: $PID)"
    fi
    rm -f "$PID_FILE"
else
    echo "⚠️  PID file not found. Trying to find and kill cloudflared process..."
    pkill -f "cloudflared tunnel" || echo "No cloudflared tunnel process found"
fi

