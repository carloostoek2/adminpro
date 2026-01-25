"""
Free Menu Handler - Menú específico para usuarios Free.

Responsabilidades:
- Mostrar menú principal Free con voz de Lucien
- Usar UserMenuProvider para generación de mensajes
- Manejar información de cola Free

Opciones:
- Mi Contenido (muestras del jardín)
- Canal VIP (información de suscripción)
- Redes Sociales (contenido gratuito)
"""
import logging
from typing import Dict, Any

from aiogram.types import Message

logger = logging.getLogger(__name__)


async def show_free_menu(message: Message, data: Dict[str, Any]):
    """
    Muestra el menú Free usando UserMenuProvider.

    Este handler genera el menú principal para usuarios Free con la voz
    consistente de Lucien, proporcionando acceso a contenido gratuito,
    información del canal VIP, y redes sociales.

    Args:
        message: Mensaje de Telegram
        data: Data del handler (incluye container, session, etc.)

    Voice Characteristics (Lucien):
    - Free users = "visitantes del jardín público"
    - Usa HTML para formato (no Markdown)
    - Usa "usted", nunca "tú"
    - Emoji 🎩 siempre presente
    - Referencias a Diana para autoridad

    Examples:
        >>> container = data.get("container")
        >>> await show_free_menu(message, data)
        >>> # Sends Free menu with Lucien-voiced greeting
    """
    user = message.from_user
    container = data.get("container")

    # Validar que el container esté disponible
    if not container:
        logger.error(f"Container no disponible para mostrar menú Free a {user.id}")
        await message.answer(
            "⚠️ Error temporal: servicio de menú no disponible. "
            "Por favor, intente nuevamente en unos momentos."
        )
        return

    try:
        # Obtener información de cola Free (para contexto futuro)
        free_queue_position = None
        try:
            free_request = await container.subscription.get_free_request(user.id)
            if free_request:
                # TODO: Calcular posición real en la cola
                # Por ahora, solo registramos que está en cola
                free_queue_position = None  # Placeholder para futura implementación
        except Exception as e:
            logger.warning(f"No se pudo obtener información de cola Free para {user.id}: {e}")

        # Obtener contexto de sesión para variación de mensajes
        session_ctx = None
        try:
            session_ctx = container.message.get_session_context(container)
        except Exception as e:
            logger.warning(f"No se pudo obtener contexto de sesión para {user.id}: {e}")

        # Generar mensaje y teclado usando UserMenuProvider
        text, keyboard = container.message.user.menu.free_menu_greeting(
            user_name=user.first_name or "visitante",
            free_queue_position=free_queue_position,
            user_id=user.id,
            session_history=session_ctx
        )

        # Enviar mensaje con formato HTML
        await message.answer(
            text,
            parse_mode="HTML",
            reply_markup=keyboard
        )

        logger.info(f"🆓 Menú Free mostrado a {user.id} (@{user.username or 'sin username'}) - voz de Lucien")

    except Exception as e:
        logger.error(f"Error mostrando menú Free a {user.id}: {e}", exc_info=True)
        await message.answer(
            "⚠️ Error al cargar el menú. Por favor, intente nuevamente."
        )
