"""
Content Service - Gestión de paquetes de contenido.

Responsibilidades:
- Crear paquetes de contenido (create_package)
- Obtener paquetes por ID (get_package)
- Listar paquetes con filtros (list_packages)
- Actualizar paquetes (update_package)
- Desactivar paquetes (deactivate_package - soft delete)
- Listar paquetes activos (get_active_packages)

Pattern: Sigue SubscriptionService (async, session injection, sin commits)
"""
import logging
from datetime import datetime
from decimal import Decimal
from typing import List, Optional, Tuple

from sqlalchemy import select, and_, or_, func
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.models import ContentPackage
from bot.database.enums import ContentCategory, PackageType

logger = logging.getLogger(__name__)


class ContentService:
    """
    Servicio para gestión de paquetes de contenido.

    CRUD Operations:
    1. Create: create_package() - Crear nuevo paquete
    2. Read: get_package() - Obtener por ID, list_packages() - Listar con filtros
    3. Update: update_package() - Actualizar campos
    4. Delete: deactivate_package() - Soft delete (is_active=False)

    Transaction Handling:
    - Los métodos NO hacen commit
    - El handler gestiona la transacción con SessionContextManager
    - Sigue patrón de SubscriptionService
    """

    def __init__(self, session: AsyncSession):
        """
        Inicializa el service.

        Args:
            session: Sesión de base de datos SQLAlchemy
        """
        self.session = session
        logger.debug("✅ ContentService inicializado")

    # ===== CREATE =====

    async def create_package(
        self,
        name: str,
        category: ContentCategory,
        description: Optional[str] = None,
        price: Optional[Decimal | float] = None,
        package_type: PackageType = PackageType.STANDARD,
        media_url: Optional[str] = None
    ) -> ContentPackage:
        """
        Crea un nuevo paquete de contenido.

        Args:
            name: Nombre del paquete (max 200 chars)
            category: Categoría (FREE_CONTENT, VIP_CONTENT, VIP_PREMIUM)
            description: Descripción detallada (opcional)
            price: Precio en moneda base (Decimal o Float)
            package_type: Tipo de paquete (default: STANDARD)
            media_url: URL del contenido (opcional)

        Returns:
            ContentPackage: Paquete creado (sin commit - handler gestiona transacción)

        Raises:
            ValueError: Si name está vacío o price es negativo
        """
        # Validaciones
        if not name or not name.strip():
            raise ValueError("El nombre del paquete no puede estar vacío")

        if name.strip() != name:
            logger.warning("⚠️ Nombre del paquete tiene espacios extra, se limpiarán")
            name = name.strip()

        # Convertir price a Decimal si es Float
        if price is not None:
            if isinstance(price, float):
                price = Decimal(str(price))
            if price < 0:
                raise ValueError("El precio no puede ser negativo")

        # Crear paquete
        package = ContentPackage(
            name=name,
            description=description,
            price=price,
            category=category,
            type=package_type,
            media_url=media_url,
            is_active=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )

        self.session.add(package)
        # NO commit - dejar que el handler gestione la transacción

        logger.info(
            f"✅ Paquete creado: {name} ({category.value}, "
            f"price={price}, type={package_type.value})"
        )

        return package

    # ===== READ =====

    async def get_package(self, package_id: int) -> Optional[ContentPackage]:
        """
        Obtiene un paquete por ID.

        Args:
            package_id: ID del paquete

        Returns:
            ContentPackage si existe, None si no
        """
        result = await self.session.execute(
            select(ContentPackage).where(ContentPackage.id == package_id)
        )
        package = result.scalar_one_or_none()

        if package:
            logger.debug(f"📦 Paquete encontrado: {package_id} - {package.name}")
        else:
            logger.debug(f"📦 Paquete no encontrado: {package_id}")

        return package

    async def list_packages(
        self,
        category: Optional[ContentCategory] = None,
        package_type: Optional[PackageType] = None,
        is_active: Optional[bool] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[ContentPackage]:
        """
        Lista paquetes con filtros opcionales.

        Args:
            category: Filtrar por categoría (opcional)
            package_type: Filtrar por tipo (opcional)
            is_active: Filtrar por estado (True=activos, False=inactivos, None=todos)
            limit: Máximo de resultados (default: 100)
            offset: Desplazamiento para paginación (default: 0)

        Returns:
            Lista de ContentPackage (ordenada por created_at DESC)
        """
        query = select(ContentPackage).order_by(ContentPackage.created_at.desc())

        # Aplicar filtros
        if category is not None:
            query = query.where(ContentPackage.category == category)

        if package_type is not None:
            query = query.where(ContentPackage.type == package_type)

        if is_active is not None:
            query = query.where(ContentPackage.is_active == is_active)

        # Aplicar paginación
        query = query.limit(limit).offset(offset)

        result = await self.session.execute(query)
        packages = list(result.scalars().all())

        logger.debug(
            f"📦 Listados {len(packages)} paquetes "
            f"(category={category}, type={package_type}, active={is_active})"
        )

        return packages

    async def get_active_packages(
        self,
        category: Optional[ContentCategory] = None,
        limit: int = 100
    ) -> List[ContentPackage]:
        """
        Obtiene solo paquetes activos (shortcut para list_packages).

        Args:
            category: Filtrar por categoría (opcional)
            limit: Máximo de resultados (default: 100)

        Returns:
            Lista de ContentPackage con is_active=True
        """
        return await self.list_packages(category=category, is_active=True, limit=limit)

    async def count_packages(
        self,
        category: Optional[ContentCategory] = None,
        is_active: Optional[bool] = None
    ) -> int:
        """
        Cuenta paquetes con filtros opcionales.

        Args:
            category: Filtrar por categoría (opcional)
            is_active: Filtrar por estado (opcional)

        Returns:
            Número de paquetes que cumplen los filtros
        """
        query = select(func.count(ContentPackage.id))

        if category is not None:
            query = query.where(ContentPackage.category == category)

        if is_active is not None:
            query = query.where(ContentPackage.is_active == is_active)

        result = await self.session.execute(query)
        count = result.scalar_one()

        logger.debug(f"📦 Conteo: {count} paquetes")

        return count

    # ===== UPDATE =====

    async def update_package(
        self,
        package_id: int,
        **kwargs
    ) -> Optional[ContentPackage]:
        """
        Actualiza campos de un paquete.

        Args:
            package_id: ID del paquete a actualizar
            **kwargs: Campos a actualizar (name, description, price, category, type, media_url)

        Returns:
            ContentPackage actualizado si existe, None si no

        Raises:
            ValueError: Si se intenta actualizar price con valor negativo

        Note:
            - Actualiza solo los campos especificados en kwargs
            - Actualiza automáticamente updated_at
        """
        package = await self.get_package(package_id)

        if not package:
            logger.warning(f"📦 Paquete no encontrado para actualizar: {package_id}")
            return None

        # Validaciones
        if 'price' in kwargs:
            price = kwargs['price']
            if price is not None:
                if isinstance(price, float):
                    kwargs['price'] = Decimal(str(price))
                if kwargs['price'] < 0:
                    raise ValueError("El precio no puede ser negativo")

        if 'name' in kwargs:
            name = kwargs['name']
            if name and name.strip() != name:
                kwargs['name'] = name.strip()

        # Actualizar campos
        for key, value in kwargs.items():
            if hasattr(package, key) and value is not None:
                setattr(package, key, value)
                logger.debug(f"📦 Actualizado {key}={value} en paquete {package_id}")

        # Actualizar timestamp
        package.updated_at = datetime.utcnow()

        # NO commit - dejar que el handler gestione la transacción

        logger.info(f"✅ Paquete actualizado: {package_id} - {package.name}")

        return package

    # ===== DELETE (Soft) =====

    async def deactivate_package(self, package_id: int) -> Optional[ContentPackage]:
        """
        Desactiva un paquete (soft delete).

        No elimina el registro, solo marca is_active=False.

        Args:
            package_id: ID del paquete a desactivar

        Returns:
            ContentPackage si existe, None si no
        """
        package = await self.get_package(package_id)

        if not package:
            logger.warning(f"📦 Paquete no encontrado para desactivar: {package_id}")
            return None

        package.is_active = False
        package.updated_at = datetime.utcnow()

        # NO commit - dejar que el handler gestione la transacción

        logger.info(f"✅ Paquete desactivado: {package_id} - {package.name}")

        return package

    async def activate_package(self, package_id: int) -> Optional[ContentPackage]:
        """
        Reactiva un paquete (soft delete undo).

        Args:
            package_id: ID del paquete a reactivar

        Returns:
            ContentPackage si existe, None si no
        """
        package = await self.get_package(package_id)

        if not package:
            logger.warning(f"📦 Paquete no encontrado para reactivar: {package_id}")
            return None

        package.is_active = True
        package.updated_at = datetime.utcnow()

        # NO commit - dejar que el handler gestione la transacción

        logger.info(f"✅ Paquete reactivado: {package_id} - {package.name}")

        return package

    async def toggle_package_active(self, package_id: int) -> Tuple[bool, Optional[ContentPackage]]:
        """
        Alterna el estado activo de un paquete.

        Args:
            package_id: ID del paquete

        Returns:
            Tuple (nuevo_estado, ContentPackage) - (True, package) si éxito, (False, None) si no existe
        """
        package = await self.get_package(package_id)

        if not package:
            return (False, None)

        package.is_active = not package.is_active
        package.updated_at = datetime.utcnow()

        # NO commit

        logger.info(
            f"✅ Paquete {'activado' if package.is_active else 'desactivado'}: "
            f"{package_id} - {package.name}"
        )

        return (True, package)

    # ===== SEARCH =====

    async def search_packages(
        self,
        search_term: str,
        is_active: Optional[bool] = None,
        limit: int = 50
    ) -> List[ContentPackage]:
        """
        Busca paquetes por nombre o descripción.

        Args:
            search_term: Término de búsqueda
            is_active: Filtrar por estado (opcional)
            limit: Máximo de resultados (default: 50)

        Returns:
            Lista de ContentPackage que coinciden con la búsqueda
        """
        search_pattern = f"%{search_term}%"

        query = select(ContentPackage).where(
            or_(
                ContentPackage.name.ilike(search_pattern),
                ContentPackage.description.ilike(search_pattern)
            )
        ).order_by(ContentPackage.created_at.desc())

        if is_active is not None:
            query = query.where(ContentPackage.is_active == is_active)

        query = query.limit(limit)

        result = await self.session.execute(query)
        packages = list(result.scalars().all())

        logger.debug(f"📦 Búsqueda '{search_term}': {len(packages)} resultados")

        return packages
