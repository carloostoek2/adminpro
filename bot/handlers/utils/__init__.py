"""
Handler utilities - Shared utilities for bot handlers.

Provides:
- Role validation helpers
- Notification helpers
- Common handler utilities
"""
from .role_check import require_vip, redirect_to_free_menu
from .notifications import send_admin_interest_notification

__all__ = ["require_vip", "redirect_to_free_menu", "send_admin_interest_notification"]
