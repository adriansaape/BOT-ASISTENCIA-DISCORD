"""
Script para ejecutar tests fácilmente
Uso: python tests/run_tests.py
"""

import subprocess
import sys

if __name__ == "__main__":
    # Ejecutar pytest con opciones útiles
    result = subprocess.run(
        [
            sys.executable, "-m", "pytest",
            "tests/",
            "-v",  # Verbose
            "--tb=short",  # Traceback corto
        ],
        cwd="."
    )
    sys.exit(result.returncode)

