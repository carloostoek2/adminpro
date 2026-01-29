"""
Health API server runner for concurrent execution with aiogram bot.

Runs FastAPI health check API in asyncio task alongside bot polling.
Allows independent monitoring even if bot experiences issues.
"""
import asyncio
import logging
import socket
import time
from typing import Optional

import uvicorn
from uvicorn.config import Config as UvicornConfig
from uvicorn.server import Server

from bot.health.endpoints import create_health_app
from config import Config

logger = logging.getLogger(__name__)


def is_port_available(host: str, port: int) -> bool:
    """Check if a port is available for binding."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.settimeout(1)
            result = sock.connect_ex((host, port))
            return result != 0  # 0 means port is in use
    except Exception:
        return False


def wait_for_port_release(host: str, port: int, timeout: int = 30) -> bool:
    """
    Wait for a port to become available.

    Args:
        host: Host to check
        port: Port to check
        timeout: Maximum time to wait in seconds

    Returns:
        True if port became available, False if timeout
    """
    logger.info(f"⏳ Esperando que el puerto {port} se libere...")
    start_time = time.time()
    while time.time() - start_time < timeout:
        if is_port_available(host, port):
            logger.info(f"✅ Puerto {port} liberado")
            return True
        time.sleep(0.5)
    logger.warning(f"⚠️ Timeout esperando puerto {port}")
    return False


async def run_health_api_with_retry(host: str, port: int, max_retries: int = 3) -> bool:
    """
    Run health API with retry logic for port binding.

    Args:
        host: Host to bind to
        port: Port to bind to
        max_retries: Maximum number of bind attempts

    Returns:
        bool: True if server started successfully, False otherwise
    """
    for attempt in range(1, max_retries + 1):
        logger.info(f"🔄 Intento {attempt}/{max_retries} de iniciar Health API...")

        # Wait for port to be available
        if not is_port_available(host, port):
            logger.warning(f"⚠️ Puerto {port} ocupado, esperando...")
            if not wait_for_port_release(host, port, timeout=10):
                logger.error(f"❌ Puerto {port} sigue ocupado")
                if attempt < max_retries:
                    continue
                return False

        # Create app
        app = create_health_app()

        # Configure uvicorn with a short timeout for shutdown
        config = UvicornConfig(
            app=app,
            host=host,
            port=port,
            log_level="info",
            access_log=True,
            loop="asyncio"
        )

        server = Server(config)

        try:
            logger.info(f"🏥 Health API starting on http://{host}:{port}")
            await server.serve()
            # If we get here, server stopped normally
            logger.info("🔌 Health API server detenido")
            return True
        except KeyboardInterrupt:
            logger.info("⌨️ Health API recibió KeyboardInterrupt")
            return True
        except asyncio.CancelledError:
            logger.info("🛑 Health API task cancelado")
            raise
        except OSError as e:
            if e.errno == 98:  # Address already in use
                logger.warning(f"⚠️ Puerto {port} se ocupó durante el bind (intento {attempt})")
                if attempt < max_retries:
                    await asyncio.sleep(1)
                    continue
            logger.error(f"❌ Error de red en Health API: {e}")
            return False
        except SystemExit as e:
            # Uvicorn may call sys.exit on some errors
            logger.error(f"❌ Health API SystemExit({e.code})")
            if attempt < max_retries:
                await asyncio.sleep(1)
                continue
            return False
        except Exception as e:
            logger.error(f"❌ Error en Health API: {e}", exc_info=True)
            if attempt < max_retries:
                await asyncio.sleep(1)
                continue
            return False

    return False


async def run_health_api(host: str, port: int) -> None:
    """
    Run FastAPI health check API server asynchronously.

    Args:
        host: Host to bind to (e.g., "0.0.0.0")
        port: Port to listen on (e.g., 8000)
    """
    success = await run_health_api_with_retry(host, port, max_retries=3)
    if not success:
        logger.error("❌ Health API no pudo iniciar después de 3 intentos")


async def start_health_server() -> Optional[asyncio.Task]:
    """
    Start health check API server as background asyncio task.

    Returns:
        asyncio.Task if started successfully, None otherwise
    """
    logger.info("🚀 Starting health API server...")

    port = Config.HEALTH_PORT
    host = Config.HEALTH_HOST

    # Quick check if port might be available
    if not is_port_available(host, port):
        logger.warning(f"⚠️ Puerto {port} parece ocupado, intentaremos de todos modos...")

    # Create asyncio task
    task = asyncio.create_task(run_health_api(host, port))

    # Wait a bit to see if it starts successfully
    await asyncio.sleep(1)

    if task.done():
        # Task finished immediately (likely failed)
        try:
            task.result()
        except Exception as e:
            logger.error(f"❌ Health API falló inmediatamente: {e}")
            return None

    logger.info(f"✅ Health API task created (host={host}, port={port})")
    return task
