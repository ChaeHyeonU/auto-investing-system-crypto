# Frontend (Next.js)

## Quickstart
```bash
cd frontend
npm install
# optional: export NEXT_PUBLIC_API_BASE_URL="http://localhost:8000"
npm run dev
```

Open `http://localhost:3000`.

## Notes
- 로그인/회원가입은 백엔드 `/v1/auth/*` API와 연결되어 있다.
- 구독 상태(`/v1/billing/subscription`)와 포트폴리오 요약(`/v1/portfolio/summary`)을 표시한다.
- 실시간 데이터(WebSocket)는 Sprint 4 범위에서 연결한다.
