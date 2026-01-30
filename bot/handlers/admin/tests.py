"""
Admin Test Runner Handler

Handler para ejecutar tests desde Telegram via comando /run_tests.
Solo accesible para administradores.
"""

import logging
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from sqlalchemy.ext.asyncio import AsyncSession

from bot.services.test_runner import TestRunnerService
from bot.middlewares import AdminAuthMiddleware

logger = logging.getLogger(__name__)

# Router para handlers de tests
tests_router = Router(name="admin_tests")

# Aplicar middleware de admin
tests_router.message.middleware(AdminAuthMiddleware())
tests_router.callback_query.middleware(AdminAuthMiddleware())


@tests_router.message(Command("run_tests"))
async def cmd_run_tests(message: Message, session: AsyncSession):
    """
    Ejecuta tests y envia reporte al admin.

    Uso:
        /run_tests - Ejecuta todos los tests
        /run_tests smoke - Ejecuta solo smoke tests
        /run_tests system - Ejecuta tests de sistema
        /run_tests coverage - Ejecuta con reporte de coverage

    Args:
        message: Mensaje del comando
        session: Sesion de BD inyectada
    """
    logger.info(f"🧪 Admin {message.from_user.id} solicito ejecucion de tests")

    # Parse arguments
    args = message.text.split()[1:] if message.text else []
    coverage = "coverage" in args
    marker = None
    test_paths = None

    if "smoke" in args:
        marker = "smoke"
    elif "system" in args:
        test_paths = ["tests/test_system/"]

    # Send "running" message
    status_msg = await message.answer(
        "🧪 <b>Ejecutando tests...</b>\n\n"
        "Esto puede tomar unos minutos."
    )

    try:
        # Create service and run tests
        runner = TestRunnerService(session)
        result = await runner.run_tests(
            test_paths=test_paths,
            coverage=coverage,
            marker=marker
        )

        # Format report
        report = runner.format_telegram_report(result)

        # Delete status message and send results
        await status_msg.delete()

        # Split if too long
        if len(report) > 4000:
            parts = [report[i:i+4000] for i in range(0, len(report), 4000)]
            for i, part in enumerate(parts):
                header = f"📊 <b>Reporte de Tests (parte {i+1}/{len(parts)})</b>\n\n"
                await message.answer(header + part, parse_mode="HTML")
        else:
            await message.answer(report, parse_mode="HTML")

        # If there are failures, offer to see details
        if result.failed > 0 or result.errors > 0:
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(
                    text="📋 Ver detalles de fallos",
                    callback_data="tests:show_failures"
                )]
            ])
            await message.answer(
                "❌ Algunos tests fallaron. ¿Deseas ver los detalles?",
                reply_markup=keyboard
            )

    except Exception as e:
        logger.exception("Error ejecutando tests")
        await status_msg.edit_text(
            f"❌ <b>Error ejecutando tests</b>\n\n"
            f"<code>{str(e)}</code>"
        )


@tests_router.callback_query(F.data == "tests:show_failures")
async def callback_show_failures(callback: CallbackQuery, session: AsyncSession):
    """Muestra detalles de tests fallidos."""
    await callback.answer("Obteniendo detalles...")

    # Note: In a production implementation, we would store the last test result
    # in a cache or database. For now, we inform the user to run tests again.
    await callback.message.answer(
        "ℹ️ <b>Informacion</b>\n\n"
        "Los detalles de fallos no estan disponibles despues de cerrar el mensaje.\n"
        "Por favor, ejecuta <code>/run_tests</code> nuevamente para ver los detalles."
    )


@tests_router.message(Command("test_status"))
async def cmd_test_status(message: Message, session: AsyncSession):
    """
    Muestra estado del sistema de tests.

    Indica si el entorno de tests esta configurado correctamente
    y cuantos tests hay disponibles.
    """
    import subprocess
    from pathlib import Path

    logger.info(f"📊 Admin {message.from_user.id} solicito estado de tests")

    try:
        project_root = Path(__file__).parent.parent.parent.parent

        # Check pytest availability
        result = subprocess.run(
            ["python", "-m", "pytest", "--collect-only", "-q"],
            capture_output=True,
            text=True,
            cwd=project_root,
            timeout=30
        )

        # Count tests
        test_count = 0
        if result.returncode == 0:
            # Count lines that look like test files
            for line in result.stdout.split("\n"):
                if "::" in line and not line.startswith("="):
                    test_count += 1

        lines = []
        lines.append("📊 <b>Estado del Sistema de Tests</b>")
        lines.append("")

        if result.returncode == 0:
            lines.append("✅ <b>pytest:</b> Disponible")
            lines.append(f"🧪 <b>Tests disponibles:</b> ~{test_count}")
        else:
            lines.append("❌ <b>pytest:</b> No disponible")
            lines.append(f"<code>{result.stderr[:200]}</code>")

        lines.append("")
        lines.append("<b>Comandos disponibles:</b>")
        lines.append("• <code>/run_tests</code> - Ejecutar todos")
        lines.append("• <code>/run_tests smoke</code> - Solo smoke tests")
        lines.append("• <code>/run_tests system</code> - Tests de sistema")
        lines.append("• <code>/run_tests coverage</code> - Con coverage")

        await message.answer("\n".join(lines), parse_mode="HTML")

    except Exception as e:
        logger.exception("Error obteniendo estado de tests")
        await message.answer(
            f"❌ <b>Error</b>\n\n"
            f"No se pudo obtener el estado: <code>{str(e)}</code>",
            parse_mode="HTML"
        )


@tests_router.message(Command("smoke_test"))
async def cmd_smoke_test(message: Message, session: AsyncSession):
    """
    Ejecuta smoke tests rapidos (alias para /run_tests smoke).

    Verificacion rapida de que el sistema funciona correctamente.
    """
    logger.info(f"🚀 Admin {message.from_user.id} solicito smoke test")

    status_msg = await message.answer(
        "🚀 <b>Ejecutando smoke tests...</b>\n\n"
        "Verificacion rapida del sistema."
    )

    try:
        runner = TestRunnerService(session)
        result = await runner.run_smoke_tests()

        report = runner.format_telegram_report(result)

        await status_msg.delete()
        await message.answer(report, parse_mode="HTML")

    except Exception as e:
        logger.exception("Error en smoke test")
        await status_msg.edit_text(
            f"❌ <b>Error en smoke test</b>\n\n"
            f"<code>{str(e)}</code>"
        )
