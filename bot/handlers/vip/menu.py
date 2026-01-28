"""
VIP Menu Handler - Menú específico para usuarios VIP.

Opciones:
- Acceso a contenido VIP
- Gestión de suscripción
- Historial de contenido
- Invitar amigos (referral)

Uses UserMenuProvider for Lucien-voiced messages with session-aware variations.
"""
import logging
from typing import Dict, Any

from aiogram.types import Message

from bot.database.enums import ContentCategory

logger = logging.getLogger(__name__)


async def show_vip_menu(message: Message, data: Dict[str, Any]):
    """
    Muestra el menú VIP usando UserMenuProvider para mensajes con voz de Lucien.

    Phase 13: If user has incomplete VIP entry flow (vip_entry_stage is set),
    redirects to entry flow instead of showing VIP menu.

    Args:
        message: Mensaje de Telegram
        data: Data del handler (incluye container, session, etc.)
    """
    user = message.from_user
    container = data.get("container")

    # Phase 13: Check for incomplete VIP entry flow
    if container:
        try:
            subscriber = await container.subscription.get_vip_subscriber(user.id)

            if subscriber and subscriber.vip_entry_stage:
                # User has incomplete entry flow - redirect to entry flow
                from bot.handlers.user.vip_entry import show_vip_entry_stage

                logger.info(
                    f"🔄 User {user.id} VIP menu redirected to entry flow "
                    f"(stage={subscriber.vip_entry_stage})"
                )

                await show_vip_entry_stage(
                    message=message,
                    container=container,
                    stage=subscriber.vip_entry_stage
                )
                return
        except Exception as e:
            logger.warning(f"⚠️ Error checking VIP entry stage for {user.id}: {e}")

    # Get VIP subscription info (original logic)
    vip_expires_at = None
    if container:
        try:
            subscriber = await container.subscription.get_vip_subscriber(user.id)
            if subscriber and subscriber.expiry_date:
                vip_expires_at = subscriber.expiry_date
        except Exception as e:
            logger.error(f"Error obteniendo info VIP para {user.id}: {e}")

    # Get session context for message variations
    session_ctx = None
    if container:
        session_ctx = container.message.get_session_context(container)

    # Generate Lucien-voiced menu message
    text, keyboard = container.message.user.menu.vip_menu_greeting(
        user_name=user.first_name,
        vip_expires_at=vip_expires_at,
        user_id=user.id,
        session_history=session_ctx
    )

    await message.answer(text, parse_mode="HTML", reply_markup=keyboard)
    logger.info(f"⭐ Menú VIP mostrado a {user.id} (voz de Lucien)")
