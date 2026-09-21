from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.core.logging import logger
from app.db.session import engine, AsyncSessionLocal, Base
from app.db.seeder import seed_cards
from app.api.v1 import routes_auth, routes_users, routes_cards, routes_recommendations

import app.models


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as db:
        await seed_cards(db)

    logger.info("Database ready.")
    yield

    await engine.dispose()
    logger.info("Server shut down.")


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description=(
            "AI-powered credit card recommendation engine. "
            "Analyzes spending behavior, credit profile, and financial goals "
            "to recommend the best credit cards with full explainability."
        ),
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    prefix = "/api/v1"
    app.include_router(routes_auth.router, prefix=prefix)
    app.include_router(routes_users.router, prefix=prefix)
    app.include_router(routes_cards.router, prefix=prefix)
    app.include_router(routes_recommendations.router, prefix=prefix)

    # ── Health check ──────────────────────────────────────────────────────────
    @app.get("/health", tags=["Health"])
    async def health():
        return {"status": "ok", "version": settings.APP_VERSION}

    return app


app = create_app()
