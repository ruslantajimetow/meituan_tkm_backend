from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.addresses import router as addresses_router
from app.api.admin import router as admin_router
from app.api.auth import router as auth_router
from app.api.menu import router as menu_router
from app.api.merchant_orders import router as merchant_orders_router
from app.api.notifications import router as notifications_router
from app.api.orders import router as orders_router
from app.api.profile import router as profile_router
from app.api.public import router as public_router
from app.api.stores import router as stores_router
from app.api.ws import router as ws_router
from app.core.config import settings
from app.core.redis import redis_client


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await redis_client.aclose()


app = FastAPI(
    title="Delivery App API",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix="/api/auth", tags=["auth"])
app.include_router(stores_router, prefix="/api/stores", tags=["stores"])
app.include_router(menu_router, prefix="/api/stores/me", tags=["menu"])
app.include_router(admin_router, prefix="/api/admin", tags=["admin"])
app.include_router(public_router, prefix="/api/public", tags=["public"])
app.include_router(orders_router, prefix="/api/orders", tags=["orders"])
app.include_router(merchant_orders_router, prefix="/api/stores/me/orders", tags=["merchant-orders"])
app.include_router(notifications_router, prefix="/api/notifications", tags=["notifications"])
app.include_router(addresses_router, prefix="/api/addresses", tags=["addresses"])
app.include_router(profile_router, prefix="/api/profile", tags=["profile"])
app.include_router(ws_router, prefix="/api/ws")


@app.get("/api/health")
async def health_check():
    return {"status": "ok"}
