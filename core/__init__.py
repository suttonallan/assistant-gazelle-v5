"""
Core modules for Assistant Gazelle V5.

Contains the API client and synchronization logic.
"""

from .gazelle_api_client import GazelleAPIClient
from .sync import SyncManager

__all__ = ['GazelleAPIClient', 'SyncManager']

