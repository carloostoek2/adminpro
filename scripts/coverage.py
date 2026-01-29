#!/usr/bin/env python3
"""
Coverage runner script.

Usage:
    python scripts/coverage.py          # Run tests with coverage
    python scripts/coverage.py --html   # Generate HTML report
    python scripts/coverage.py --open   # Open HTML report in browser
"""
import subprocess
import sys
import argparse
import webbrowser
from pathlib import Path


def run_coverage(html=False, open_report=False, fail_under=None):
    """Run pytest with coverage reporting."""
    cmd = [
        "pytest",
        "--cov=bot",
        "--cov=config",
        "--cov=main",
        "--cov-report=term-missing:skip-covered",
    ]

    if html or open_report:
        cmd.append("--cov-report=html")

    if fail_under:
        cmd.append(f"--cov-fail-under={fail_under}")

    # Add any additional arguments passed to the script
    cmd.extend(sys.argv[1:])

    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd)

    if open_report and result.returncode == 0:
        report_path = Path("htmlcov/index.html").absolute()
        if report_path.exists():
            print(f"\nOpening coverage report: {report_path}")
            webbrowser.open(f"file://{report_path}")

    return result.returncode


def main():
    parser = argparse.ArgumentParser(description="Run tests with coverage")
    parser.add_argument(
        "--html", action="store_true",
        help="Generate HTML coverage report"
    )
    parser.add_argument(
        "--open", action="store_true",
        help="Open HTML report in browser after running"
    )
    parser.add_argument(
        "--fail-under", type=int, metavar="PERCENT",
        help="Fail if coverage is below PERCENT"
    )

    args, remaining = parser.parse_known_args()

    # Pass remaining args to pytest
    sys.argv = [sys.argv[0]] + remaining

    return run_coverage(
        html=args.html or args.open,
        open_report=args.open,
        fail_under=args.fail_under
    )


if __name__ == "__main__":
    sys.exit(main())
