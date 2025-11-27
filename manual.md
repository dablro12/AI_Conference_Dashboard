## 📦 주요 스크립트 안내

---

### 1️⃣ 백그라운드 실행

```bash
./scripts/docker_compose_run_background.sh
```

- **Docker Compose**를 빌드 및 백그라운드 실행  
- **Cloudflare Tunnel**을 백그라운드로 실행  
- 외부 접속 **URL**을 `.cloudflare_url` 에 저장  
- 로그는 `logs/cloudflare_tunnel.log` 에 기록  
- 프로세스 **PID**를 `.cloudflare_tunnel.pid` 에 저장

---

### 2️⃣ 상태 확인

```bash
./scripts/status.sh
```

- Docker 컨테이너 상태,  
- Cloudflare Tunnel 동작 여부,  
- 외부 접속 URL 정보를 확인

---

### 3️⃣ Cloudflare Tunnel 중지

```bash
./scripts/stop_tunnel.sh
```

- Cloudflare Tunnel 프로세스 종료

---

## 📝 사용 예시

|           작업           |             명령어              |
|:-----------------------:|:------------------------------:|
| **백그라운드로 시작**   | `./scripts/docker_compose_run_background.sh` |
| **서비스 상태 확인**    | `./scripts/status.sh`           |
| **로그 모니터링**       | `tail -f logs/cloudflare_tunnel.log` |
| **Cloudflare Tunnel 중지** | `./scripts/stop_tunnel.sh`              |

---

