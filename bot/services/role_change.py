"""
Role Change Service - Registra cambios de rol para auditoría.

Responsabilidades:
- Registrar cambios de rol en tabla UserRoleChangeLog
- Proporcionar historial de cambios por usuario
- Integrar con SubscriptionService para cambios automáticos (VIP expiración)
- Seguir patrón stateless (sin caché, solo logging)

Pattern: Sigue SubscriptionService (async, session injection, sin commits)
"""
import logging
from datetime import datetime
from typing import Optional, Dict, Any, List

from sqlalchemy import select, desc, func
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.models import UserRoleChangeLog
from bot.database.enums import UserRole, RoleChangeReason

logger = logging.getLogger(__name__)


class RoleChangeService:
    """
    Servicio para registro de cambios de rol.

    Uso:
        # Log cambio manual por admin
        await service.log_role_change(
            user_id=123456,
            new_role=UserRole.VIP,
            changed_by=789012,  # Admin ID
            reason=RoleChangeReason.VIP_REDEEMED,
            change_source="ADMIN_PANEL",
            change_metadata={"token": "ABC123", "duration_hours": 24}
        )

        # Log cambio automático (VIP expiración)
        await service.log_role_change(
            user_id=123456,
            new_role=UserRole.FREE,
            changed_by=0,  # SYSTEM
            reason=RoleChangeReason.VIP_EXPIRED,
            change_source="SYSTEM",
            change_metadata={"expired_at": "2024-01-01 12:00:00"}
        )
    """

    def __init__(self, session: AsyncSession):
        """
        Inicializa el service.

        Args:
            session: Sesión de base de datos SQLAlchemy
        """
        self.session = session
        logger.debug("✅ RoleChangeService inicializado")

    async def log_role_change(
        self,
        user_id: int,
        new_role: UserRole,
        changed_by: int,
        reason: RoleChangeReason,
        change_source: str = "SYSTEM",
        previous_role: Optional[UserRole] = None,
        change_metadata: Optional[Dict[str, Any]] = None
    ) -> UserRoleChangeLog:
        """
        Registra un cambio de rol en la tabla de auditoría.

        Args:
            user_id: ID del usuario que cambió de rol
            new_role: Nuevo rol del usuario
            changed_by: ID del admin que hizo el cambio (0 para SYSTEM)
            reason: Razón del cambio (RoleChangeReason enum)
            change_source: Origen del cambio ("ADMIN_PANEL", "SYSTEM", "API")
            previous_role: Rol anterior (opcional - se detecta automáticamente si None)
            change_metadata: Información adicional JSON (opcional)

        Returns:
            UserRoleChangeLog: Registro creado (sin commit - handler gestiona transacción)

        Raises:
            ValueError: Si change_source no es válido
        """
        # Validar change_source
        valid_sources = ["ADMIN_PANEL", "SYSTEM", "API"]
        if change_source not in valid_sources:
            raise ValueError(f"change_source inválido: {change_source}. Debe ser: {valid_sources}")

        # Si previous_role no se proporciona, intentar detectarlo
        if previous_role is None:
            previous_role = await self._detect_previous_role(user_id)

        # Crear registro
        log_entry = UserRoleChangeLog(
            user_id=user_id,
            previous_role=previous_role,
            new_role=new_role,
            changed_by=changed_by,
            reason=reason,
            change_source=change_source,
            change_metadata=change_metadata,
            changed_at=datetime.utcnow()
        )

        self.session.add(log_entry)
        # NO commit - dejar que el handler gestione la transacción

        logger.info(
            f"📝 Cambio de rol registrado: user {user_id} "
            f"{previous_role.value if previous_role else 'NEW'} → {new_role.value} "
            f"(reason: {reason.value}, by: {changed_by})"
        )

        return log_entry

    async def _detect_previous_role(self, user_id: int) -> Optional[UserRole]:
        """
        Detecta el rol anterior del usuario.

        Intenta obtener el último rol registrado en UserRoleChangeLog.
        Si no hay registros, retorna None (usuario nuevo).

        Args:
            user_id: ID del usuario

        Returns:
            UserRole anterior o None si no hay registros
        """
        # Buscar último cambio de rol para este usuario
        query = (
            select(UserRoleChangeLog)
            .where(UserRoleChangeLog.user_id == user_id)
            .order_by(desc(UserRoleChangeLog.changed_at))
            .limit(1)
        )

        result = await self.session.execute(query)
        last_change = result.scalar_one_or_none()

        if last_change:
            return last_change.new_role

        # No hay registros previos (usuario nuevo)
        logger.debug(f"📝 Usuario {user_id} no tiene registros previos de rol (nuevo usuario)")
        return None

    async def get_user_role_history(
        self,
        user_id: int,
        limit: int = 50,
        offset: int = 0
    ) -> List[UserRoleChangeLog]:
        """
        Obtiene historial de cambios de rol de un usuario.

        Args:
            user_id: ID del usuario
            limit: Máximo de resultados (default: 50)
            offset: Desplazamiento para paginación (default: 0)

        Returns:
            Lista de UserRoleChangeLog ordenada por fecha descendente
        """
        query = (
            select(UserRoleChangeLog)
            .where(UserRoleChangeLog.user_id == user_id)
            .order_by(desc(UserRoleChangeLog.changed_at))
            .limit(limit)
            .offset(offset)
        )

        result = await self.session.execute(query)
        history = list(result.scalars().all())

        logger.debug(f"📝 Historial obtenido: {len(history)} cambios para user {user_id}")

        return history

    async def get_recent_role_changes(
        self,
        limit: int = 100,
        offset: int = 0
    ) -> List[UserRoleChangeLog]:
        """
        Obtiene cambios de rol recientes (todos los usuarios).

        Args:
            limit: Máximo de resultados (default: 100)
            offset: Desplazamiento para paginación (default: 0)

        Returns:
            Lista de UserRoleChangeLog ordenada por fecha descendente
        """
        query = (
            select(UserRoleChangeLog)
            .order_by(desc(UserRoleChangeLog.changed_at))
            .limit(limit)
            .offset(offset)
        )

        result = await self.session.execute(query)
        changes = list(result.scalars().all())

        logger.debug(f"📝 Cambios recientes obtenidos: {len(changes)} registros")

        return changes

    async def get_changes_by_admin(
        self,
        admin_id: int,
        limit: int = 100,
        offset: int = 0
    ) -> List[UserRoleChangeLog]:
        """
        Obtiene cambios de rol realizados por un admin específico.

        Args:
            admin_id: ID del admin
            limit: Máximo de resultados (default: 100)
            offset: Desplazamiento para paginación (default: 0)

        Returns:
            Lista de UserRoleChangeLog ordenada por fecha descendente
        """
        query = (
            select(UserRoleChangeLog)
            .where(UserRoleChangeLog.changed_by == admin_id)
            .order_by(desc(UserRoleChangeLog.changed_at))
            .limit(limit)
            .offset(offset)
        )

        result = await self.session.execute(query)
        changes = list(result.scalars().all())

        logger.debug(f"📝 Cambios por admin {admin_id}: {len(changes)} registros")

        return changes

    async def count_role_changes(self, user_id: Optional[int] = None) -> int:
        """
        Cuenta cambios de rol (opcionalmente filtrado por usuario).

        Args:
            user_id: ID del usuario para filtrar (opcional)

        Returns:
            Número de cambios de rol
        """
        query = select(func.count(UserRoleChangeLog.id))

        if user_id is not None:
            query = query.where(UserRoleChangeLog.user_id == user_id)

        result = await self.session.execute(query)
        count = result.scalar_one()

        logger.debug(f"📝 Conteo cambios de rol: {count} (user_id={user_id})")

        return count
