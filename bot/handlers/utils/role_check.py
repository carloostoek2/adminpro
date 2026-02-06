"""
Role validation utilities for bot handlers.

Provides helpers to validate user roles and handle unauthorized access attempts.
"""
import logging
from typing import Optional

from aiogram.types import CallbackQuery, Message

from bot.database.enums import UserRole

logger = logging.getLogger(__name__)


async def get_user_role_from_container(container, user_id: int) -> Optional[UserRole]:
    """
    Get user role from container's role detection service.

    Args:
        container: ServiceContainer with role_detection service
        user_id: Telegram user ID

    Returns:
        UserRole enum value or None if error
    """
    try:
        role_service = container.role_detection
        return await role_service.get_user_role(user_id)
    except Exception as e:
        logger.error(f"Error getting user role for {user_id}: {e}")
        return None


async def require_vip(
    callback: CallbackQuery,
    container,
    redirect: bool = True
) -> bool:
    """
    Verifica que el usuario sea VIP o Admin.

    Si el usuario es Free y redirect=True, muestra mensaje de error
    y redirige al menú Free.

    Args:
        callback: CallbackQuery de Telegram
        container: ServiceContainer con role_detection
        redirect: Si True, redirige a menú Free si no es VIP

    Returns:
        True si el usuario tiene acceso (VIP/Admin), False si no
    """
    user = callback.from_user

    # Get user role
    user_role = await get_user_role_from_container(container, user.id)

    if user_role is None:
        logger.error(f"No se pudo determinar rol para usuario {user.id}")
        await callback.answer(
            "⚠️ Error verificando permisos. Intente nuevamente.",
            show_alert=True
        )
        return False

    # Allow VIP and Admin roles
    if user_role in (UserRole.VIP, UserRole.ADMIN):
        return True

    # User is Free - log and optionally redirect
    logger.warning(
        f"🚫 Usuario Free {user.id} ({user.username or 'no_username'}) "
        f"intentó acceder a función VIP: {callback.data}"
    )

    await callback.answer(
        "⚠️ Esta sección es exclusiva para miembros VIP",
        show_alert=True
    )

    if redirect:
        await redirect_to_free_menu(callback, container)

    return False


async def redirect_to_free_menu(callback: CallbackQuery, container) -> None:
    """
    Redirige usuario al menú Free.

    Args:
        callback: CallbackQuery de Telegram
        container: ServiceContainer
    """
    try:
        from bot.handlers.free.menu import show_free_menu

        data = {"container": container}
        await show_free_menu(
            callback.message,
            data,
            user_id=callback.from_user.id,
            user_first_name=callback.from_user.first_name,
            edit_mode=True
        )
        logger.info(f"🔄 Usuario {callback.from_user.id} redirigido al menú Free")
    except Exception as e:
        logger.error(f"Error redirigiendo al menú Free: {e}")
        # Don't raise - we already showed error message to user
