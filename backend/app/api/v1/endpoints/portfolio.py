from fastapi import APIRouter, Depends

from app.api.deps import get_current_user
from app.models.user import User

router = APIRouter()


@router.get("/summary")
def portfolio_summary(current_user: User = Depends(get_current_user)) -> dict[str, float]:
    _ = current_user
    return {
        "total_equity": 10000.0,
        "available_balance": 8200.0,
        "unrealized_pnl": 150.0,
        "realized_pnl": 250.0,
        "daily_return_pct": 1.2,
        "max_drawdown_pct": -3.1,
        "sharpe_30d": 1.4,
    }
