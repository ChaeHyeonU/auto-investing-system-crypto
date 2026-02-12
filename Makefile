.PHONY: help up down backend frontend migrate

help:
	@echo "Targets:"
	@echo "  up        - start local infra (postgres, redis)"
	@echo "  down      - stop local infra"
	@echo "  backend   - run backend (expects venv setup)"
	@echo "  frontend  - run frontend (expects npm install)"
	@echo "  migrate   - run alembic migrations"

up:
	docker compose -f infra/docker-compose.yml up -d

down:
	docker compose -f infra/docker-compose.yml down

backend:
	cd backend && uvicorn app.main:app --reload --port 8000

frontend:
	cd frontend && npm run dev

migrate:
	cd backend && alembic upgrade head
