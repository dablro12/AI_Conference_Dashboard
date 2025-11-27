#!/bin/bash

# 서비스 상태 확인 스크립트

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
URL_FILE="$PROJECT_DIR/.cloudflare_url"
PID_FILE="$PROJECT_DIR/.cloudflare_tunnel.pid"

echo "📊 Service Status"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Docker Compose 상태
echo "🐳 Docker Containers:"
cd "$PROJECT_DIR"
docker compose ps
echo ""

# Cloudflare Tunnel 상태
echo "🌐 Cloudflare Tunnel:"
if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    if ps -p "$PID" > /dev/null 2>&1; then
        echo "   ✅ Running (PID: $PID)"
    else
        echo "   ❌ Not running (stale PID file)"
    fi
else
    if pgrep -f "cloudflared tunnel" > /dev/null; then
        echo "   ⚠️  Running but PID file not found"
    else
        echo "   ❌ Not running"
    fi
fi

# URL 정보
if [ -f "$URL_FILE" ]; then
    URL=$(cat "$URL_FILE")
    echo ""
    echo "🌍 Website URL:"
    echo "   $URL"
else
    echo ""
    echo "⚠️  URL file not found"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

