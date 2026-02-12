from fastapi import APIRouter

from app.api.v1.endpoints import auth, billing, portfolio, strategies

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(billing.router, prefix="/billing", tags=["billing"])
api_router.include_router(strategies.router, prefix="/strategies", tags=["strategies"])
api_router.include_router(portfolio.router, prefix="/portfolio", tags=["portfolio"])

