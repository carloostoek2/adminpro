"""
Message Service Package

Provides centralized message generation with Lucien's voice consistency.

Architecture:
- BaseMessageProvider: Abstract base enforcing stateless interface
- CommonMessages: Shared messages (errors, success, greetings)
- LucienVoiceService: Main service container for all message providers

All providers are stateless: no session/bot stored as instance variables.
All messages use formatters from bot.utils.formatters for dates/numbers.

Usage in handlers:
    from bot.services.container import ServiceContainer

    # Lazy-loaded via ServiceContainer.message property
    msg = container.message.common.error('something failed')
    msg = container.message.common.success('action completed')
"""

from .base import BaseMessageProvider
from .common import CommonMessages

# Direct imports for type hints and external access
from .admin_main import AdminMainMessages
from .admin_vip import AdminVIPMessages
from .admin_free import AdminFreeMessages

__all__ = [
    "BaseMessageProvider",
    "CommonMessages",
    "LucienVoiceService",
    "AdminMessages",
    "AdminMainMessages",
    "AdminVIPMessages",
    "AdminFreeMessages",
]


class AdminMessages:
    """
    Admin messages namespace for organization.

    Provides access to AdminMainMessages, AdminVIPMessages, AdminFreeMessages.
    Each submenu has its own provider organized by navigation flow.

    Architecture:
        LucienVoiceService
            └─ admin: AdminMessages (this class)
                ├─ main: AdminMainMessages (Phase 2 Plan 03) ✅
                ├─ vip: AdminVIPMessages (Phase 2 Plan 01) ✅
                └─ free: AdminFreeMessages (Phase 2 Plan 02) ✅

    Usage:
        container = ServiceContainer(session, bot)

        # Access main menu messages
        text, kb = container.message.admin.main.admin_menu_greeting(is_configured=True)

        # Access VIP messages
        text, kb = container.message.admin.vip.vip_menu(is_configured=True)

        # Access Free messages
        text, kb = container.message.admin.free.free_menu(is_configured=True)

    Stateless Design:
        All sub-providers are lazy-loaded and stateless.
        No session or bot stored as instance variables.
    """

    def __init__(self):
        """
        Initialize admin namespace with lazy-loaded sub-providers.

        Sub-providers created on first access to minimize memory footprint.
        """
        self._main = None
        self._vip = None
        self._free = None

    @property
    def main(self):
        """
        Main admin menu messages (Phase 2 Plan 03) ✅ COMPLETE.

        Lazy-loaded: creates AdminMainMessages instance on first access.

        Returns:
            AdminMainMessages: Provider for main admin menu messages

        Examples:
            >>> admin = AdminMessages()
            >>> text, kb = admin.main.admin_menu_greeting(is_configured=True)
            >>> '🎩' in text and 'custodio' in text.lower()
            True
        """
        if self._main is None:
            from .admin_main import AdminMainMessages
            self._main = AdminMainMessages()
        return self._main

    @property
    def vip(self):
        """
        VIP admin messages (Phase 2 Plan 01) ✅ COMPLETE.

        Lazy-loaded: creates AdminVIPMessages instance on first access.

        Returns:
            AdminVIPMessages: Provider for VIP management messages

        Examples:
            >>> admin = AdminMessages()
            >>> text, kb = admin.vip.vip_menu(is_configured=True)
            >>> '🎩' in text
            True
        """
        if self._vip is None:
            from .admin_vip import AdminVIPMessages
            self._vip = AdminVIPMessages()
        return self._vip

    @property
    def free(self):
        """
        Free admin messages (Phase 2 Plan 02) ✅ COMPLETE.

        Lazy-loaded: creates AdminFreeMessages instance on first access.

        Returns:
            AdminFreeMessages: Provider for Free channel management messages

        Examples:
            >>> admin = AdminMessages()
            >>> text, kb = admin.free.free_menu(is_configured=True)
            >>> '🎩' in text
            True
        """
        if self._free is None:
            from .admin_free import AdminFreeMessages
            self._free = AdminFreeMessages()
        return self._free


class LucienVoiceService:
    """
    Main message service providing access to all message providers.

    This service is stateless and integrated into ServiceContainer with lazy loading.
    Organizes message providers by navigation flow (admin/, user/) for discoverability.

    Architecture:
        ServiceContainer
            └─ LucienVoiceService (this class)
                ├─ common: CommonMessages ✅
                ├─ admin: AdminMessages ✅ PHASE 2 COMPLETE
                │   ├─ main: AdminMainMessages ✅
                │   ├─ vip: AdminVIPMessages ✅
                │   └─ free: AdminFreeMessages ✅
                └─ user: UserMessages (Phase 3 - Future)

    Voice Consistency:
        All providers inherit from BaseMessageProvider which enforces Lucien's voice.
        See docs/guia-estilo.md for complete voice guidelines.

    Stateless Design:
        This service does NOT store session or bot as instance variables.
        All context passed to message methods via parameters.
        Prevents memory leaks and database session leaks.

    Usage:
        container = ServiceContainer(session, bot)

        # Common messages
        error_msg = container.message.common.error('context')

        # Admin main menu
        text, kb = container.message.admin.main.admin_menu_greeting(is_configured=True)

        # Admin VIP messages
        text, kb = container.message.admin.vip.vip_menu(is_configured=True)

        # Admin Free messages
        text, kb = container.message.admin.free.free_menu(is_configured=True)
    """

    def __init__(self):
        """
        Initialize message service with lazy-loaded providers.

        Providers are created on first access to minimize memory footprint.
        """
        self._common = None
        self._admin = None

    @property
    def common(self) -> CommonMessages:
        """
        Common messages provider (errors, success, not_found).

        Lazy-loaded: creates CommonMessages instance on first access.

        Returns:
            CommonMessages: Provider for shared messages
        """
        if self._common is None:
            self._common = CommonMessages()
        return self._common

    @property
    def admin(self) -> AdminMessages:
        """
        Admin messages namespace.

        Lazy-loaded: creates AdminMessages namespace on first access.
        Provides access to admin.main, admin.vip, admin.free sub-providers.

        Returns:
            AdminMessages: Namespace for admin message providers

        Examples:
            >>> service = LucienVoiceService()
            >>> text, kb = service.admin.vip.vip_menu(is_configured=True)
            >>> '🎩' in text
            True
        """
        if self._admin is None:
            self._admin = AdminMessages()
        return self._admin
