"""
Router package initialization.
"""

from app.routers.voice import router as voice_router
from app.routers.crm import router as crm_router

__all__ = ["voice_router", "crm_router"]
