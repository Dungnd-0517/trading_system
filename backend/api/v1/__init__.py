from fastapi import APIRouter

from api.v1.market import router as market_router
from api.v1.news import router as news_router
from api.v1.orders import router as orders_router
from api.v1.simulation import router as simulation_router
from api.v1.websocket import router as websocket_router

router = APIRouter()
router.include_router(market_router, prefix="/market", tags=["market"])
router.include_router(orders_router, prefix="/orders", tags=["orders"])
router.include_router(simulation_router, prefix="/simulation", tags=["simulation"])
router.include_router(news_router, prefix="/news", tags=["news"])
router.include_router(websocket_router, tags=["stream"])