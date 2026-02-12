# auto-investing-system-crypto

웹 로그인 기반 구독형 AI 암호화폐 투자 자동화 시스템 프로젝트다.

## Repository Structure
- `backend/`: FastAPI 기반 API 서버 스캐폴드
- `frontend/`: Next.js 기반 대시보드 스캐폴드
- `infra/`: 로컬 인프라(`docker-compose`) + Terraform 골격
- `docs/`: PRD, 아키텍처, 백로그, ERD, OpenAPI 문서

## Quickstart
### 1) Local infra
```bash
make up
```

### 2) Backend
```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

### 3) Frontend
```bash
cd frontend
npm install
# optional: export NEXT_PUBLIC_API_BASE_URL="http://localhost:8000"
npm run dev
```

## Docs
- PRD: `docs/PRD.md`
- Architecture: `docs/TECH_ARCHITECTURE_SPEC.md`
- MVP Sprint Backlog: `docs/MVP_SPRINT_BACKLOG.md`
- ERD: `docs/ERD.md`
- OpenAPI: `docs/API_OPENAPI.yaml`
- Sprint 1 GitHub Issues: `docs/SPRINT1_GITHUB_ISSUES.md`
