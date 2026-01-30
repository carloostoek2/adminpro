"""
Test Runner Service

Servicio para ejecutar tests desde el bot, con soporte para
reportes formateados y notificaciones a administradores.
"""

import asyncio
import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


@dataclass
class TestResult:
    """Resultado de una ejecucion de tests."""
    returncode: int
    passed: int
    failed: int
    errors: int
    skipped: int
    total: int
    duration_seconds: float
    stdout: str
    stderr: str
    coverage_percent: Optional[float] = None

    @property
    def success(self) -> bool:
        """True si todos los tests pasaron."""
        return self.returncode == 0 and self.failed == 0 and self.errors == 0

    @property
    def summary(self) -> str:
        """Resumen en una linea."""
        return (
            f"Tests: {self.total} total, "
            f"{self.passed} passed, "
            f"{self.failed} failed, "
            f"{self.errors} errors, "
            f"{self.skipped} skipped"
        )


class TestRunnerService:
    """
    Servicio para ejecutar tests pytest desde el bot.

    Ejecuta tests en subprocess aislado para evitar que
    errores afecten el proceso principal del bot.
    """

    def __init__(self, session: AsyncSession, project_root: Optional[Path] = None):
        self.session = session
        self.project_root = project_root or Path(__file__).parent.parent.parent
        self._lock = asyncio.Lock()

    async def run_tests(
        self,
        test_paths: Optional[List[str]] = None,
        coverage: bool = False,
        marker: Optional[str] = None,
        timeout: int = 300
    ) -> TestResult:
        """
        Ejecuta tests y retorna resultado estructurado.

        Args:
            test_paths: Paths especificos a testear (None = todos)
            coverage: Si True, incluye coverage
            marker: Marker de pytest para filtrar tests
            timeout: Timeout en segundos para la ejecucion

        Returns:
            TestResult con metricas y output
        """
        async with self._lock:
            # Build command
            cmd = ["python", "-m", "pytest"]

            if coverage:
                cmd.extend(["--cov=bot", "--cov-report=term"])

            if marker:
                cmd.extend(["-m", marker])

            cmd.extend(test_paths or ["tests/"])
            cmd.extend(["-v", "--tb=short"])

            # Execute in subprocess
            logger.info(f"Ejecutando tests: {' '.join(cmd)}")

            try:
                proc = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    cwd=self.project_root
                )

                stdout, stderr = await asyncio.wait_for(
                    proc.communicate(),
                    timeout=timeout
                )

                stdout_str = stdout.decode("utf-8", errors="replace")
                stderr_str = stderr.decode("utf-8", errors="replace")

                # Parse results
                result = self._parse_results(
                    proc.returncode or 0,
                    stdout_str,
                    stderr_str
                )

                logger.info(f"Tests completados: {result.summary}")
                return result

            except asyncio.TimeoutError:
                logger.error(f"Tests timeout despues de {timeout}s")
                proc.kill()
                return TestResult(
                    returncode=-1,
                    passed=0, failed=0, errors=1, skipped=0, total=0,
                    duration_seconds=timeout,
                    stdout="",
                    stderr=f"Timeout despues de {timeout} segundos"
                )

    def _parse_results(
        self,
        returncode: int,
        stdout: str,
        stderr: str
    ) -> TestResult:
        """Parsea output de pytest para extraer metricas."""
        output = stdout + "\n" + stderr

        # Initialize defaults
        passed = failed = errors = skipped = 0
        duration = 0.0
        coverage_percent = None

        # Parse summary line like: "50 passed, 2 failed, 1 error in 12.34s"
        # or: "50 passed, 2 failed, 1 error, 3 skipped in 12.34s"
        summary_pattern = r"(\d+) passed(?:, (\d+) failed)?(?:, (\d+) error)?(?:, (\d+) skipped)? in ([\d.]+)s"
        match = re.search(summary_pattern, output)

        if match:
            passed = int(match.group(1)) if match.group(1) else 0
            failed = int(match.group(2)) if match.group(2) else 0
            errors = int(match.group(3)) if match.group(3) else 0
            skipped = int(match.group(4)) if match.group(4) else 0
            duration = float(match.group(5)) if match.group(5) else 0.0

        total = passed + failed + errors + skipped

        # Parse coverage percentage
        coverage_pattern = r"TOTAL\s+\d+\s+\d+\s+(\d+)%"
        coverage_match = re.search(coverage_pattern, output)
        if coverage_match:
            coverage_percent = float(coverage_match.group(1))

        return TestResult(
            returncode=returncode,
            passed=passed,
            failed=failed,
            errors=errors,
            skipped=skipped,
            total=total,
            duration_seconds=duration,
            stdout=stdout,
            stderr=stderr,
            coverage_percent=coverage_percent
        )

    async def run_smoke_tests(self) -> TestResult:
        """Ejecuta solo smoke tests (verificacion rapida)."""
        return await self.run_tests(marker="smoke", timeout=60)

    async def run_system_tests(self) -> TestResult:
        """Ejecuta tests del sistema."""
        return await self.run_tests(test_paths=["tests/test_system/"])

    def format_telegram_report(self, result: TestResult, max_length: int = 4000) -> str:
        """
        Formatea resultado para enviar por Telegram.

        Args:
            result: Resultado de tests
            max_length: Longitud maxima del mensaje

        Returns:
            Texto formateado en HTML
        """
        lines = []

        # Header with status
        if result.success:
            lines.append("✅ <b>TODOS LOS TESTS PASARON</b>")
        else:
            lines.append("❌ <b>ALGUNOS TESTS FALLARON</b>")
        lines.append("")

        # Metrics table
        lines.append("📊 <b>Metricas:</b>")
        lines.append(f"  • Total: {result.total}")
        lines.append(f"  • ✅ Pasados: {result.passed}")
        lines.append(f"  • ❌ Fallidos: {result.failed}")
        lines.append(f"  • ⚠️ Errores: {result.errors}")
        lines.append(f"  • ⏭️ Saltados: {result.skipped}")
        lines.append("")

        # Duration
        lines.append(f"⏱️ <b>Duracion:</b> {result.duration_seconds:.2f}s")

        # Coverage if available
        if result.coverage_percent is not None:
            lines.append(f"📈 <b>Coverage:</b> {result.coverage_percent:.1f}%")

        # Failed tests details (if any)
        if result.failed > 0 or result.errors > 0:
            lines.append("")
            lines.append("📝 <b>Tests fallidos:</b>")

            # Extract failed test names
            failed_pattern = r"FAILED\s+(\S+)"
            failed_tests = re.findall(failed_pattern, result.stdout + result.stderr)

            for test in failed_tests[:5]:  # Show first 5
                # Escape HTML special characters
                test_escaped = test.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                lines.append(f"  ❌ <code>{test_escaped}</code>")

            if len(failed_tests) > 5:
                lines.append(f"  ... y {len(failed_tests) - 5} mas")

        report = "\n".join(lines)

        # Truncate if exceeds max_length
        if len(report) > max_length:
            truncated = report[:max_length - 100]
            truncated += "\n\n<i>(Mensaje truncado por limite de longitud)</i>"
            return truncated

        return report

    def get_failed_test_details(self, result: TestResult, max_tests: int = 3) -> str:
        """
        Extrae detalles de tests fallidos para mostrar.

        Args:
            result: Resultado de tests
            max_tests: Maximo numero de tests a mostrar

        Returns:
            Texto formateado con detalles de fallos
        """
        if result.failed == 0 and result.errors == 0:
            return "✅ No hay tests fallidos."

        lines = []
        lines.append("📋 <b>Detalles de fallos:</b>")
        lines.append("")

        # Split output by test sections
        output = result.stdout + "\n" + result.stderr

        # Find failed test sections
        failed_pattern = r"(FAILED|ERROR)\s+(\S+)\s*\n.*?\n(?=FAILED|ERROR|PASSED|=+|$)"
        matches = re.findall(failed_pattern, output, re.DOTALL)

        for i, (status, test_name) in enumerate(matches[:max_tests]):
            if i > 0:
                lines.append("")

            # Escape HTML
            test_escaped = test_name.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            lines.append(f"<b>{status}:</b> <code>{test_escaped}</code>")

            # Extract traceback
            section_match = re.search(
                rf"{re.escape(status)}\s+{re.escape(test_name)}.*?\n(.*?)(?=FAILED|ERROR|PASSED|=+|$)",
                output,
                re.DOTALL
            )
            if section_match:
                traceback = section_match.group(1).strip()
                # Limit traceback length
                if len(traceback) > 500:
                    traceback = traceback[:500] + "\n..."
                # Escape HTML
                traceback_escaped = traceback.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                lines.append(f"<pre>{traceback_escaped}</pre>")

        if len(matches) > max_tests:
            lines.append(f"\n<i>... y {len(matches) - max_tests} fallos mas</i>")

        return "\n".join(lines)
