"""
API router: assembles all sub-routers under the /api prefix.
Import this single router in main.py.
"""

from fastapi import APIRouter
from api.routes import jobs, exports, speakers, content, events, mux, settings

router = APIRouter(prefix="/api")

router.include_router(jobs.router)
router.include_router(exports.router)
router.include_router(speakers.router)
router.include_router(content.router)
router.include_router(events.router)
router.include_router(mux.router)
router.include_router(settings.router)

