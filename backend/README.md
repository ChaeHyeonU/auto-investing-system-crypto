# Backend (FastAPI)

## Quickstart
```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
# optional: use postgres instead of sqlite default
# export DATABASE_URL="postgresql+psycopg://app:app@localhost:5432/auto_investing"
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

API docs:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Test
```bash
cd backend
source .venv/bin/activate
pytest
```

## Migration
```bash
cd backend
source .venv/bin/activate
alembic upgrade head
```
