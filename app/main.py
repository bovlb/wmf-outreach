"""FastAPI application entry point."""
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
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
            "user_courses_enriched": "/api/users/{username}?enrich=true",
            "user_active_staff": "/api/users/{username}/active-staff",
            "course_users": "/api/courses/{school}/{title_slug}/users",
            "course_details": "/api/courses/{school}/{title_slug}",
        },
        "gadget": {
            "javascript": "/gadget/outreach-staff-gadget.js",
            "interface": "/gadget/course-staff.html?username={username}",
        },
    }


# Gadget static files
STATIC_DIR = Path(__file__).parent.parent / "static"


@app.get("/gadget/outreach-staff-gadget.js")
async def serve_gadget_js():
    """Serve the MediaWiki gadget JavaScript."""
    js_file = STATIC_DIR / "outreach-staff-gadget.js"
    return FileResponse(
        js_file,
        media_type="application/javascript",
        headers={"Cache-Control": "no-cache"}  # For development
    )


@app.get("/gadget/course-staff.html", response_class=HTMLResponse)
async def serve_gadget_html():
    """Serve the course staff display page."""
    html_file = STATIC_DIR / "course-staff.html"
    return FileResponse(
        html_file,
        media_type="text/html",
        headers={"Cache-Control": "no-cache"}  # For development
    )
