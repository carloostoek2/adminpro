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

__all__ = ["BaseMessageProvider", "CommonMessages", "LucienVoiceService"]


class LucienVoiceService:
    """
    Main message service providing access to all message providers.

    This service is stateless and integrated into ServiceContainer with lazy loading.
    Organizes message providers by navigation flow (admin/, user/) for discoverability.

    Architecture:
        ServiceContainer
            └─ LucienVoiceService (this class)
                ├─ common: CommonMessages
                ├─ admin: AdminMessages (Phase 2)
                └─ user: UserMessages (Phase 3)

    Voice Consistency:
        All providers inherit from BaseMessageProvider which enforces Lucien's voice.
        See docs/guia-estilo.md for complete voice guidelines.

    Stateless Design:
        This service does NOT store session or bot as instance variables.
        All context passed to message methods via parameters.
        Prevents memory leaks and database session leaks.

    Usage:
        container = ServiceContainer(session, bot)

        # Lazy-loaded: CommonMessages loads on first access
        error_msg = container.message.common.error('context')

        # Reuses cached CommonMessages instance
        success_msg = container.message.common.success('action')
    """

    def __init__(self):
        """
        Initialize message service with lazy-loaded providers.

        Providers are created on first access to minimize memory footprint.
        """
        self._common = None

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
