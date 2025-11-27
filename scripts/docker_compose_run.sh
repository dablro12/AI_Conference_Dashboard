#!/bin/bash

# Docker Compose 빌드 및 실행 후 Cloudflare Tunnel 자동 시작

set -e

echo "🐳 Building and starting Docker containers..."
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
echo "🌐 Starting Cloudflare Tunnel..."

# Cloudflare Tunnel 실행 및 URL만 출력
cloudflared tunnel --url http://localhost:5000 2>&1 | while IFS= read -r line; do
    # URL 패턴 찾기 (https://xxxx-xxxx-xxxx.trycloudflare.com 형식)
    if echo "$line" | grep -qE 'https://[a-zA-Z0-9-]+\.trycloudflare\.com'; then
        URL=$(echo "$line" | grep -oE 'https://[a-zA-Z0-9-]+\.trycloudflare\.com' | head -1)
        if [ -n "$URL" ]; then
            echo ""
            echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
            echo "🌍 Your website is now accessible at:"
            echo "   $URL"
            echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
            echo ""
        fi
    fi
done