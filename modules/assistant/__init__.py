"""
Module Assistant Conversationnel V5.

Assistant conversationnel pour interroger la base de données Gazelle
via langage naturel avec recherche vectorielle et parsing intelligent.

Migré depuis V4 (Flask + SQL Server) vers V5 (FastAPI + Supabase).
"""

from .conversation_handler import ConversationHandler

__version__ = "5.0.0"
__all__ = ['ConversationHandler']
