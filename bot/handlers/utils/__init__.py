"""
Handler utilities - Shared utilities for bot handlers.

Provides:
- Role validation helpers
- Common handler utilities
"""
from .role_check import require_vip, redirect_to_free_menu

__all__ = ["require_vip", "redirect_to_free_menu"]
