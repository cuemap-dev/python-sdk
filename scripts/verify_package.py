"""Build and install the Python SDK into a clean virtual environment."""

from __future__ import annotations

import subprocess
import sys
import tempfile
import venv
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def run(*args: str, cwd: Path = ROOT) -> None:
    subprocess.run(args, cwd=cwd, check=True)


with tempfile.TemporaryDirectory(prefix="cuemap-python-pack-") as temporary:
    output = Path(temporary) / "dist"
    output.mkdir()
    run(sys.executable, "-m", "build", "--no-isolation", "--sdist", "--wheel", "--outdir", str(output))

    environment = Path(temporary) / "venv"
    venv.EnvBuilder(with_pip=True).create(environment)
    python = environment / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
    wheel = next(output.glob("cuemap-0.7.2-*.whl"))
    run(str(python), "-m", "pip", "install", "--no-deps", str(wheel), cwd=Path(temporary))
    run(
        str(python),
        "-c",
        "import cuemap; from cuemap import AsyncCueMap, CueMap, EmbeddedCueMap; assert cuemap.__version__ == '0.7.2'",
        cwd=Path(temporary),
    )

print("verified the Python wheel in a fresh virtual environment")
