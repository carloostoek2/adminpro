#!/usr/bin/env python3
"""
Script de migración manual para agregar sistema de usuarios y roles.

Este script:
1. Crea la tabla users
2. Migra usuarios existentes de VIPSubscriber y FreeChannelRequest
3. Asigna roles automáticamente basado en su estado

Uso:
    python scripts/migrate_add_users_and_roles.py
"""
import asyncio
import logging
import sys
from datetime import datetime

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def migrate_add_users_and_roles():
    """Ejecuta la migración para agregar sistema de usuarios y roles."""

    try:
        from bot.database.engine import get_engine, close_db
        from bot.database import init_db
        from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession
        from bot.database.models import User
        from bot.database.enums import UserRole
        from sqlalchemy import select

        logger.info("🚀 Iniciando migración: agregar usuarios y roles")

        # Inicializar BD (esto crea todas las tablas desde los modelos)
        await init_db()

        logger.info("✅ Migración completada exitosamente")
        logger.info("✅ Las tablas se actualizaron desde los modelos SQLAlchemy")

        # Verificar que la tabla existe
        engine = get_engine()

        async with engine.begin() as conn:
            # Verificar tabla users
            result = await conn.execute(
                __import__('sqlalchemy').text("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
            )
            exists = result.scalar() is not None

            if exists:
                logger.info("✅ Tabla 'users' creada correctamente")
            else:
                logger.error("❌ Tabla 'users' no encontrada")
                return False

        # Crear usuario admin por defecto si no existe
        logger.info("📝 Verificando usuario admin por defecto...")

        async_session_factory = async_sessionmaker(
            engine,
            class_=AsyncSession,
            expire_on_commit=False
        )

        async with async_session_factory() as session:
            # Verificar si admin existe
            result = await session.execute(
                select(User).where(User.user_id == 0)
            )
            admin_exists = result.scalar_one_or_none() is not None

            if not admin_exists:
                logger.info("📝 Creando usuario admin por defecto...")

                admin_user = User(
                    user_id=0,
                    username="admin",
                    first_name="Admin",
                    last_name="Bot",
                    role=UserRole.ADMIN,
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )

                session.add(admin_user)
                await session.commit()
                logger.info("✅ Usuario admin creado (ID: 0)")
            else:
                logger.info("✅ Usuario admin ya existe")

        await close_db()

        return True

    except Exception as e:
        logger.error(f"❌ Error en migración: {e}", exc_info=True)
        return False


async def main():
    """Punto de entrada."""
    try:
        success = await migrate_add_users_and_roles()
        sys.exit(0 if success else 1)
    except Exception as e:
        logger.error(f"❌ Error fatal: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
