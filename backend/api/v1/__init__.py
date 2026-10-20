from fastapi import APIRouter

from api.v1.agents_governor import router as agents_governor_router
from api.v1.agents_news import router as agents_news_router
from api.v1.agents_reflexion import router as agents_reflexion_router
from api.v1.agents_technical import router as agents_technical_router
from api.v1.chat import router as chat_router
from api.v1.governor import router as governor_router
from api.v1.knowledge import router as knowledge_router
from api.v1.market import router as market_router
from api.v1.news import router as news_router
from api.v1.orders import router as orders_router
from api.v1.reflexion import router as reflexion_router
from api.v1.simulation import router as simulation_router
from api.v1.strategy import router as strategy_router
from api.v1.websocket import router as websocket_router

router = APIRouter()
router.include_router(chat_router, prefix="/chat", tags=["chat"])
router.include_router(agents_governor_router, prefix="/agents/governor", tags=["agents-governor"])
router.include_router(agents_news_router, prefix="/agents/news", tags=["agents-news"])
router.include_router(agents_reflexion_router, prefix="/agents/reflexion", tags=["agents-reflexion"])
router.include_router(agents_technical_router, prefix="/agents/technical", tags=["agents-technical"])
router.include_router(governor_router, prefix="/governor", tags=["governor"])
router.include_router(knowledge_router, prefix="/knowledge", tags=["knowledge"])
router.include_router(reflexion_router, prefix="/reflexion", tags=["reflexion"])
router.include_router(market_router, prefix="/market", tags=["market"])
router.include_router(orders_router, prefix="/orders", tags=["orders"])
router.include_router(simulation_router, prefix="/simulation", tags=["simulation"])
router.include_router(news_router, prefix="/news", tags=["news"])
router.include_router(strategy_router, prefix="/strategy", tags=["strategy"])
router.include_router(websocket_router, tags=["stream"])