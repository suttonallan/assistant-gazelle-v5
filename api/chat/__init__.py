"""
Chat Intelligent API - Point d'entrée journée technicien.
"""

from .schemas import (
    ChatRequest,
    ChatResponse,
    DayOverview,
    AppointmentDetail,
    AppointmentOverview,
    ComfortInfo,
    BillingInfo,
    TimelineEntry
)
from .service import ChatService

__all__ = [
    "ChatRequest",
    "ChatResponse",
    "DayOverview",
    "AppointmentDetail",
    "AppointmentOverview",
    "ComfortInfo",
    "BillingInfo",
    "TimelineEntry",
    "ChatService",
]
