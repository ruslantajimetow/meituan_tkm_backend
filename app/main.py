import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.addresses import router as addresses_router
from app.api.admin import router as admin_router
from app.api.auth import router as auth_router
from app.api.menu import router as menu_router
from app.api.merchant_orders import router as merchant_orders_router
from app.api.notifications import router as notifications_router
from app.api.orders import router as orders_router
from app.api.profile import router as profile_router
from app.api.public import router as public_router
from app.api.messages import router as messages_router
from app.api.ratings import router as ratings_router
from app.api.stores import router as stores_router
from app.api.ws import router as ws_router
from app.core.config import settings
from app.core.errors import Errors
from app.core.redis import redis_client

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await redis_client.aclose()


app = FastAPI(
    title="Delivery App API",
    version="0.1.0",
    lifespan=lifespan,
)


@app.exception_handler(RequestValidationError)
async def validation_error_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
    """Return the first validation error as a user-readable message."""
    errors = exc.errors()
    first = errors[0] if errors else {}
    field = " → ".join(str(loc) for loc in first.get("loc", [])[1:])
    msg = first.get("msg", "Invalid input.")
    detail = {"code": "VALIDATION_ERROR", "message": f"{field}: {msg}" if field else msg}
    return JSONResponse(status_code=422, content={"detail": detail})


@app.exception_handler(Exception)
async def unhandled_exception_handler(_: Request, exc: Exception) -> JSONResponse:
    """Catch-all for unhandled exceptions — log the traceback, return a safe message."""
    logger.exception("Unhandled exception: %s", exc)
    return JSONResponse(status_code=500, content={"detail": Errors.internal()})


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
app.include_router(ratings_router, prefix="/api/ratings", tags=["ratings"])
app.include_router(messages_router, prefix="/api/messages", tags=["messages"])
app.include_router(ws_router, prefix="/api/ws")


@app.get("/api/health")
async def health_check():
    return {"status": "ok"}
