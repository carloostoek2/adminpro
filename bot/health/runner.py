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
            sock.settimeout(1)
            result = sock.connect_ex((host, port))
            return result != 0  # 0 means port is in use
    except Exception:
        return False


def wait_for_port_release(host: str, port: int, timeout: int = 10) -> bool:
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


async def run_health_api(host: str, port: int) -> None:
    """
    Run FastAPI health check API server asynchronously.

    Creates and configures uvicorn server to run FastAPI app
    in the existing asyncio event loop. Runs forever until cancelled.

    Args:
        host: Host to bind to (e.g., "0.0.0.0" for all interfaces)
        port: Port to listen on (e.g., 8000)

    Returns:
        None (runs indefinitely until cancelled or KeyboardInterrupt)

    Note:
        - Uses "asyncio" loop mode to share event loop with bot
        - Enables access logging for monitoring
        - Handles KeyboardInterrupt gracefully
        - Properly shuts down server on cancellation to release port
    """
    # Create FastAPI app
    app = create_health_app()

    # Configure uvicorn
    uvicorn_config = UvicornConfig(
        app=app,
        host=host,
        port=port,
        log_level="info",
        access_log=True,
        loop="asyncio"  # Use existing event loop
    )

    # Create server
    server = Server(uvicorn_config)

    # Log startup
    logger.info(f"🏥 Health API starting on http://{host}:{port}")

    try:
        # Run server (blocking until cancelled)
        await server.serve()
    except KeyboardInterrupt:
        logger.info("⌨️ Health API recibió KeyboardInterrupt")
    except asyncio.CancelledError:
        logger.info("🛑 Health API task cancelado - iniciando shutdown...")
        # CancelledError indica que debemos cerrar limpiamente
        raise  # Re-raise para que el caller sepa que fue cancelado
    except Exception as e:
        logger.error(f"❌ Error en Health API server: {e}", exc_info=True)
    finally:
        # Asegurar que el servidor se cierre y libere el puerto
        if server.started:
            logger.info("🔌 Cerrando servidor Health API...")
            server.should_exit = True
            # Dar tiempo al servidor para cerrar conexiones
            await asyncio.sleep(0.5)
        logger.info("🔌 Health API server detenido")


async def start_health_server() -> asyncio.Task:
    """
    Start health check API server as background asyncio task.

    Gets configuration from Config.HEALTH_PORT and Config.HEALTH_HOST,
    creates asyncio task for run_health_api(), and returns task reference.

    Waits for port to be available if it was recently released (handles
    rapid restarts where the port might still be in TIME_WAIT state).

    Returns:
        asyncio.Task: Task object for tracking and graceful shutdown

    Raises:
        Exception: If task creation fails (logged, caught by caller)

    Note:
        Task runs in background and does not block bot startup.
        Store task reference for graceful shutdown in on_shutdown().
    """
    logger.info("🚀 Starting health API server...")

    # Get configuration
    port = Config.HEALTH_PORT
    host = Config.HEALTH_HOST  # Default: "0.0.0.0" for external access

    # Check if port is available, wait if needed (handles rapid restarts)
    if not is_port_available(host, port):
        logger.warning(f"⚠️ Puerto {port} está ocupado, esperando liberación...")
        if not wait_for_port_release(host, port, timeout=10):
            logger.error(f"❌ Puerto {port} sigue ocupado después de 10s")
            logger.error("   Posible causa: proceso anterior no terminó limpiamente")
            logger.error("   Solución: kill $(lsof -t -i:{port}) o esperar 60s")

    # Create asyncio task for health API
    task = asyncio.create_task(run_health_api(host, port))

    logger.info(f"✅ Health API task created (host={host}, port={port})")

    return task
