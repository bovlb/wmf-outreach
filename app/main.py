"""FastAPI application entry point."""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.cache.redis import cache
from app.api import health, users, courses


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup and shutdown.
    
    Establishes Redis connection on startup and closes it on shutdown.
    """
    # Startup
    await cache.connect()
    yield
    # Shutdown
    await cache.disconnect()


# Create FastAPI app
app = FastAPI(
    title="Outreach Dashboard Helper",
    description="Cached API for Outreach Dashboard data",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS middleware for gadget access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust for production
    allow_credentials=True,
    allow_methods=["GET"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router, tags=["Health"])
app.include_router(users.router, prefix="/api", tags=["Users"])
app.include_router(courses.router, prefix="/api", tags=["Courses"])


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "service": "Outreach Dashboard Helper",
        "version": "0.1.0",
        "endpoints": {
            "health": "/health",
            "user_courses": "/api/users/{username}",
            "course_users": "/api/courses/{school}/{title_slug}/users",
            "course_details": "/api/courses/{school}/{title_slug}",
        },
    }
