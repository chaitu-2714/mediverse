"""
MediVerse AI — FastAPI Backend Authentication Server.
Integrates with Supabase Authentication, PostgreSQL database, and implements
production-ready OAuth 2.0 flows, JWT sessions, refresh tokens, and rate limiting.
"""
from __future__ import annotations

import os
import sys
import logging
import traceback
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

# Add project root to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import get_settings
from backend.routers.auth import router as auth_router

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("mediverse.backend")

settings = get_settings()

app = FastAPI(
    title="MediVerse AI Authentication Backend",
    version="1.0.0",
    description="Production-grade secure backend for MediVerse AI Identity Management using Supabase Auth."
)

# Enable CORS for desktop app and localhost
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=".*",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Custom middleware to log requests and handle exceptions dynamically
@app.middleware("http")
async def log_and_error_handling_middleware(request: Request, call_next):
    logger.info(f"Incoming Request: {request.method} {request.url.path}")
    try:
        response = await call_next(request)
        return response
    except Exception as e:
        tb = traceback.format_exc()
        logger.error(f"Backend crashed on request {request.method} {request.url.path}:\n{tb}")
        error_details = {
            "success": False,
            "error": f"Internal Server Error: {str(e)}",
            "exception_type": type(e).__name__,
            "traceback": tb.splitlines()
        }
        return JSONResponse(
            status_code=500,
            content=error_details
        )

# Mount the auth router
app.include_router(auth_router)

logger.info("FastAPI auth application initialized with Supabase.")
