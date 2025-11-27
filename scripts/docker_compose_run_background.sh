#!/bin/bash

# Docker Compose 빌드 및 실행 후 Cloudflare Tunnel 백그라운드 실행

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
LOG_DIR="$PROJECT_DIR/logs"
URL_FILE="$PROJECT_DIR/.cloudflare_url"
PID_FILE="$PROJECT_DIR/.cloudflare_tunnel.pid"

# 로그 디렉토리 생성
mkdir -p "$LOG_DIR"

echo "🐳 Building and starting Docker containers..."
cd "$PROJECT_DIR"
docker compose up --build -d

echo "⏳ Waiting for services to be ready..."
sleep 5

# 서비스가 정상적으로 실행 중인지 확인
if ! docker compose ps | grep -q "Up"; then
    echo "❌ Error: Docker containers failed to start"
    docker compose logs
    exit 1
fi

echo "✅ Docker containers are running"

# 기존 Cloudflare Tunnel 프로세스가 있으면 종료
if [ -f "$PID_FILE" ]; then
    OLD_PID=$(cat "$PID_FILE")
    if ps -p "$OLD_PID" > /dev/null 2>&1; then
        echo "🛑 Stopping existing Cloudflare Tunnel (PID: $OLD_PID)..."
        kill "$OLD_PID" 2>/dev/null || true
        sleep 2
    fi
    rm -f "$PID_FILE"
fi

echo "🌐 Starting Cloudflare Tunnel in background..."

# Cloudflare Tunnel을 백그라운드로 실행
nohup cloudflared tunnel --url http://localhost:5000 > "$LOG_DIR/cloudflare_tunnel.log" 2>&1 &
TUNNEL_PID=$!

# PID 저장
echo $TUNNEL_PID > "$PID_FILE"

echo "✅ Cloudflare Tunnel started (PID: $TUNNEL_PID)"
echo "📝 Logs are being written to: $LOG_DIR/cloudflare_tunnel.log"

# URL 추출을 위해 잠시 대기
echo "⏳ Waiting for tunnel URL..."
sleep 5

# 로그에서 URL 추출
if [ -f "$LOG_DIR/cloudflare_tunnel.log" ]; then
    URL=$(grep -oE 'https://[a-zA-Z0-9-]+\.trycloudflare\.com' "$LOG_DIR/cloudflare_tunnel.log" | head -1)
    if [ -n "$URL" ]; then
        echo "$URL" > "$URL_FILE"
        echo ""
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo "🌍 Your website is now accessible at:"
        echo "   $URL"
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo ""
        echo "📋 URL saved to: $URL_FILE"
        echo "📊 View logs: tail -f $LOG_DIR/cloudflare_tunnel.log"
        echo "🛑 Stop tunnel: ./scripts/stop_tunnel.sh"
    else
        echo "⚠️  URL not found yet. Check logs: tail -f $LOG_DIR/cloudflare_tunnel.log"
    fi
fi

echo ""
echo "✅ All services are running in background!"
echo "   - Docker containers: docker compose ps"
echo "   - Cloudflare Tunnel: PID $TUNNEL_PID"
echo "   - View URL: cat $URL_FILE"
echo "   - View logs: tail -f $LOG_DIR/cloudflare_tunnel.log"

