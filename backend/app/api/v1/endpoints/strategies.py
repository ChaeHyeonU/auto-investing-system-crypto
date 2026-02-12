from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


class StrategyCreateRequest(BaseModel):
    profile: str
    mode: str


@router.get("")
def list_strategies() -> list[dict[str, str]]:
    return [{"id": "strategy-stub", "profile": "balanced", "mode": "paper", "status": "draft"}]


@router.post("")
def create_strategy(payload: StrategyCreateRequest) -> dict[str, str]:
    return {"id": "strategy-stub", "profile": payload.profile, "mode": payload.mode, "status": "draft"}


@router.post("/{strategy_id}/activate")
def activate_strategy(strategy_id: str) -> dict[str, str]:
    return {"id": strategy_id, "status": "active"}

