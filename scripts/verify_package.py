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
    wheels = sorted(output.glob("cuemap-*.whl"))
    if len(wheels) != 1:
        raise RuntimeError(f"expected exactly one CueMap wheel, found {len(wheels)}")
    wheel = wheels[0]
    run(str(python), "-m", "pip", "install", "--no-deps", str(wheel), cwd=Path(temporary))
    run(
        str(python),
        "-c",
        """
import importlib.metadata
import cuemap
from cuemap import AsyncCueMap, CueMap, EmbeddedCueMap

package_version = importlib.metadata.version("cuemap")
assert cuemap.__version__ == package_version, (
    f"version mismatch: package={cuemap.__version__}, distribution={package_version}"
)
print(f"verified installed version {package_version}")
""",
        cwd=Path(temporary),
    )

print("verified the Python wheel in a fresh virtual environment")
