"""
Lean MVP Backend
================

FastAPI server for the Buyer Intelligence platform.
Handles scraping, listing management, and (later) the BI pipeline.

Run: uvicorn main:app --reload --port 8000
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import settings
import database

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)


# =============================================================================
# LIFECYCLE
# =============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    # Startup
    logger.info("🚀 Starting Lean MVP Backend...")
    logger.info(f"   Port: {settings.PORT}")
    logger.info(f"   Debug: {settings.DEBUG}")
    
    # Check database connectivity
    try:
        db_ok = await database.check_health()
        if db_ok:
            logger.info("   Database: ✓ Connected")
        else:
            logger.error("   Database: ✗ Connection failed")
    except Exception as e:
        logger.error(f"   Database: ✗ {e}")
    
    yield
    
    # Shutdown
    logger.info("Shutting down...")
    await database.close_pool()


# =============================================================================
# APP
# =============================================================================

app = FastAPI(
    title="Lean MVP - Buyer Intelligence API",
    description="Property intelligence platform with AI-powered renovation analysis",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS - Allow all origins for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=False,  # Must be False when using wildcard origins
    allow_methods=["*"],
    allow_headers=["*"],
)


# =============================================================================
# ROUTES
# =============================================================================

# Import and include routers
from routes.scrape import router as scrape_router
from routes.listings import router as listings_router
from routes.building_context import router as building_context_router
from routes.curation_v2 import router as curation_router  # Production curation (Foursquare + Transitland)
from routes.story import router as story_router
from routes.translate import router as translate_router  # Multi-language translation
from routes.v2_routes import router as v2_router  # V2 Pipeline (clean)
from routes.v3_routes import router as v3_router  # V3 Pipeline
from routes.admin_routes import router as admin_router  # Admin — run status & logs

app.include_router(scrape_router, prefix="/api", tags=["Scraping"])
app.include_router(listings_router, prefix="/api", tags=["Listings"])
app.include_router(building_context_router, prefix="/api", tags=["Building Context"])
app.include_router(curation_router, prefix="/api", tags=["Place Curation"])
app.include_router(story_router, prefix="/api", tags=["Stories"])
app.include_router(translate_router, prefix="/api", tags=["Translation"])
app.include_router(v2_router, tags=["V2 Pipeline"])  # Already has /api prefix
app.include_router(v3_router, tags=["V3 Pipeline"])  # Already has /api prefix
app.include_router(admin_router, tags=["Admin"])  # Already has /api prefix


# =============================================================================
# HEALTH CHECK
# =============================================================================

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    db_ok = await database.check_health()
    return {
        "status": "ok" if db_ok else "degraded",
        "database": "connected" if db_ok else "disconnected",
        "version": "1.0.0"
    }


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": "Lean MVP - Buyer Intelligence API",
        "version": "1.0.0",
        "docs": "/docs"
    }


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG
    )

