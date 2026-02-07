"""
Notification Utilities - Funciones compartidas para notificaciones.

Este módulo centraliza la lógica de notificaciones para evitar duplicación
y seguir el principio DRY (Don't Repeat Yourself).
"""
import logging
from typing import TYPE_CHECKING

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import Config

if TYPE_CHECKING:
    from bot.services.container import ServiceContainer

logger = logging.getLogger(__name__)


async def send_admin_interest_notification(
    bot,
    container: "ServiceContainer",
    user,
    package,
    interest,
    user_role: str
):
    """
    Envía notificación privada a todos los admins sobre nuevo interés.

    Esta función centralizada evita la duplicación de código entre
    los handlers de callbacks Free y VIP.

    Args:
        bot: Instancia del bot
        container: ServiceContainer
        user: Usuario de Telegram (callback.from_user)
        package: Objeto ContentPackage
        interest: Objeto UserInterest
        user_role: "VIP" o "Free"
    """
    try:
        # Get all admin user IDs from config (environment variable)
        admin_ids = Config.ADMIN_USER_IDS

        if not admin_ids:
            logger.warning("⚠️ No admins configured for interest notifications")
            return

        # Format user info
        username = f"@{user.username}" if user.username else f"usuario {user.id}"
        user_link = f"tg://user?id={user.id}"

        # Format package info using enum properties directly
        package_type_emoji = package.category.emoji if package.category else "📦"
        category_display = package.category.display_name if package.category else "Desconocido"

        # Build notification message in Lucien's voice
        notification_text = (
            f"🎩 <b>Lucien:</b> <i>Nueva expresión de interés detectada...</i>\n\n"
            f"<b>👤 Visitante:</b> {username} ({user_role})\n"
            f"<b>📦 Tesoro de interés:</b> {package_type_emoji} {package.name}\n"
            f"<b>📝 Descripción:</b> {package.description or 'Sin descripción'}\n"
        )

        if package.price is not None:
            notification_text += f"<b>💰 Precio:</b> ${package.price:.2f}"
        else:
            notification_text += "<b>💰 Precio:</b> Acceso promocional"

        if package.category:
            notification_text += f"\n<b>🏷️ Tipo:</b> {category_display}"

        notification_text += (
            f"\n\n<b>⏰ Momento:</b> {interest.created_at.strftime('%Y-%m-%d %H:%M')}\n"
            f"<i>Diana, un visitante del jardín ha mostrado interés en uno de sus tesoros...</i>"
        )

        # Create inline keyboard with action buttons
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📋 Ver Todos los Intereses",
                    callback_data=f"admin:interests:list:pending"
                )
            ],
            [
                InlineKeyboardButton(
                    text="✅ Marcar como Atendido",
                    callback_data=f"admin:interest:attend:{interest.id}"
                )
            ],
            [
                InlineKeyboardButton(
                    text="💬 Mensaje al Usuario",
                    url=user_link
                ),
                InlineKeyboardButton(
                    text="🚫 Bloquear Contacto",
                    callback_data=f"admin:user:block_contact:{user.id}"
                )
            ]
        ])

        # Send notification to all admins
        sent_count = 0
        failed_admins = []

        for admin_id in admin_ids:
            try:
                await bot.send_message(
                    chat_id=admin_id,
                    text=notification_text,
                    parse_mode="HTML",
                    reply_markup=keyboard
                )
                sent_count += 1
                logger.debug(f"📤 Interest notification sent to admin {admin_id}")
            except Exception as e:
                logger.error(
                    f"❌ Failed to send interest notification to admin {admin_id}: {e}"
                )
                failed_admins.append(admin_id)

        logger.info(
            f"📢 Interest notification sent to {sent_count}/{len(admin_ids)} admins "
            f"(user: {user.id}, package: {package.id}, role: {user_role})"
        )

        if failed_admins:
            logger.warning(
                f"⚠️ Failed to send to admins: {failed_admins} "
                f"(may have blocked the bot or deleted chat)"
            )

    except Exception as e:
        logger.error(f"Error sending admin interest notification: {e}", exc_info=True)


__all__ = ["send_admin_interest_notification"]
