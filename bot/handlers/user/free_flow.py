"""
Free Flow Handler - Solicitud de acceso al canal Free.

⚠️ ESTE HANDLER ESTÁ DESACTIVADO ⚠️

RATIONALE:
Los usuarios llegan al canal por link público directo, no saben del bot hasta después.
El flujo real es: Usuario → "Unirse" en canal → ChatJoinRequest (free_join_request.py)

Este handler (callback "user:request_free") solo funcionaría si el usuario:
1. Ya conoce el bot
2. Tiene el bot abierto
3. Presiona un botón dentro del bot

Eso NO ocurre en la práctica. Nadie usa este flujo.

EL FLUJO ACTIVO ES: free_join_request.py (ChatJoinRequest)
"""
import logging
# from aiogram import F
# from aiogram.types import CallbackQuery
# from sqlalchemy.ext.asyncio import AsyncSession

# from bot.handlers.user.start import user_router
# from bot.services.container import ServiceContainer

logger = logging.getLogger(__name__)


# ========================================================================
# ⚠️ HANDLER DESACTIVADO - Usar free_join_request.py en su lugar
# ========================================================================
# Razón: Los usuarios llegan por link directo al canal, no por el bot.
# El flujo es: "Unirse" en canal → ChatJoinRequest → free_join_request.py
#
# Si en el futuro queremos que los usuarios soliciten desde el bot:
# 1. Necesitamos una manera de que descubran el bot ANTES del canal
# 2. Promocionar el bot en otros canales/grupos
# 3. Entonces este handler podría ser útil
#
# Por ahora, TODO el flujo Free está en free_join_request.py
# ========================================================================

# @user_router.callback_query(F.data == "user:request_free")
# async def callback_request_free(
#     callback: CallbackQuery,
#     session: AsyncSession
# ):
#     """
#     Procesa solicitud de acceso al canal Free.
#
#     ⚠️ ESTE HANDLER NO SE USA - Ver free_join_request.py
#
#     Args:
#         callback: Callback query
#         session: Sesión de BD
#     """
#     ... (código comentado) ...
