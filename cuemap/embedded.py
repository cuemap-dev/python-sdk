"""Lifecycle management for a local CueMap engine process."""

from __future__ import annotations

import json
import os
import platform
import shutil
import socket
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Mapping, Optional
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def _normalize_url(url: str) -> str:
    return url.rstrip("/")


def _inspect_engine(url: str, api_key: Optional[str] = None) -> str:
    headers = {"X-API-Key": api_key} if api_key else {}
    try:
        with urlopen(Request(f"{_normalize_url(url)}/", headers=headers), timeout=0.75) as response:
            payload = json.loads(response.read(16_384))
        return "cuemap" if payload.get("name") == "CueMap Rust Engine" else "occupied"
    except HTTPError:
        return "occupied"
    except (URLError, TimeoutError, OSError, ValueError, json.JSONDecodeError):
        return "closed"


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
        listener.bind(("127.0.0.1", 0))
        return int(listener.getsockname()[1])


def _platform_package() -> str:
    operating_system = {"Windows": "win32", "Darwin": "darwin", "Linux": "linux"}.get(platform.system())
    machine = platform.machine().lower()
    architecture = {"arm64": "arm64", "aarch64": "arm64", "amd64": "x64", "x86_64": "x64"}.get(machine)
    if operating_system is None or architecture is None or (operating_system == "win32" and architecture != "x64"):
        raise RuntimeError(f"Unsupported CueMap platform: {platform.system()} {machine}")
    return f"@cuemap-dev/engine-{operating_system}-{architecture}"


def _npm_global_binary() -> Optional[str]:
    npm = shutil.which("npm")
    if not npm:
        return None
    npm_command = [npm]
    if platform.system() == "Windows":
        node = shutil.which("node")
        npm_cli = Path(npm).parent / "node_modules" / "npm" / "bin" / "npm-cli.js"
        if not node or not npm_cli.is_file():
            return None
        npm_command = [node, str(npm_cli)]
    try:
        root = subprocess.run(
            [*npm_command, "root", "--global"],
            check=True,
            capture_output=True,
            text=True,
            timeout=5,
        ).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return None
    package_bin = Path(root) / _platform_package() / "bin"
    candidate = package_bin / ("cuemap-native.exe" if platform.system() == "Windows" else "cuemap")
    return str(candidate) if candidate.is_file() else None


def resolve_cuemap_binary(explicit_path: Optional[str] = None) -> str:
    """Resolve an engine binary without downloading or mutating the machine."""

    configured = explicit_path or os.environ.get("CUEMAP_BIN")
    if configured:
        path = Path(configured).expanduser()
        if not path.is_file():
            raise FileNotFoundError(f"CueMap executable does not exist: {path}")
        return str(path)

    installed = shutil.which("cuemap")
    if installed and Path(installed).suffix.lower() not in {".cmd", ".bat", ".ps1"}:
        return installed

    global_binary = _npm_global_binary()
    if global_binary:
        return global_binary

    workspace = Path(__file__).resolve().parents[2] / "rust_engine" / "target"
    binary_name = "cuemap.exe" if os.name == "nt" else "cuemap"
    source_binaries = [
        workspace / profile / binary_name
        for profile in ("release", "debug")
        if (workspace / profile / binary_name).is_file()
    ]
    if source_binaries:
        return str(max(source_binaries, key=lambda candidate: candidate.stat().st_mtime))

    raise FileNotFoundError(
        "Could not find the CueMap engine. Set CUEMAP_BIN, install `cuemap` on PATH, "
        f"or install the native npm package {_platform_package()}."
    )


@dataclass
class EmbeddedCueMap:
    """A verified engine connection and, when applicable, its owned process."""

    url: str
    owned: bool
    _process: Optional[subprocess.Popen] = None
    _shutdown_timeout: float = 5.0

    @classmethod
    def start(
        cls,
        *,
        url: Optional[str] = None,
        bin_path: Optional[str] = None,
        port: int = 8735,
        config_path: Optional[str] = None,
        api_key: Optional[str] = None,
        startup_timeout: float = 15.0,
        shutdown_timeout: float = 5.0,
        env: Optional[Mapping[str, str]] = None,
        logger: Optional[Callable[[str], None]] = None,
    ) -> "EmbeddedCueMap":
        log = logger or (lambda _message: None)
        if url:
            normalized = _normalize_url(url)
            if _inspect_engine(normalized, api_key) != "cuemap":
                raise ConnectionError(f"No CueMap engine is reachable at {normalized}")
            log(f"Attached to CueMap at {normalized}")
            return cls(normalized, False, _shutdown_timeout=shutdown_timeout)

        preferred_url = f"http://127.0.0.1:{port}"
        status = _inspect_engine(preferred_url, api_key)
        if status == "cuemap":
            log(f"Attached to CueMap at {preferred_url}")
            return cls(preferred_url, False, _shutdown_timeout=shutdown_timeout)

        selected_port = _free_port() if status == "occupied" else port
        selected_url = f"http://127.0.0.1:{selected_port}"
        executable = resolve_cuemap_binary(bin_path)
        command = [executable]
        if platform.system() == "Windows" and Path(executable).suffix.lower() != ".exe":
            if Path(executable).suffix.lower() in {".cmd", ".bat", ".ps1"}:
                raise ValueError("Use the native .exe or the npm package bin/cuemap wrapper, not a shell shim")
            node = shutil.which("node")
            if not node:
                raise FileNotFoundError("Node.js is required to launch the CueMap npm wrapper")
            command = [node, executable]
        arguments = [*command, "start", "--port", str(selected_port)]
        if config_path:
            arguments.extend(["--config", str(Path(config_path).expanduser())])
        process_env = dict(os.environ)
        if env:
            process_env.update(env)
        process_env["CUEMAP_PORT"] = str(selected_port)
        process_env["CUEMAP_HOST"] = "127.0.0.1"
        tokenizer = Path(executable).parent.parent / "assets" / "en_tokenizer.bin"
        if Path(executable).name == "cuemap-native.exe" and tokenizer.is_file():
            process_env.setdefault("TOKENIZER_PATH", str(tokenizer))
        if api_key:
            process_env["CUEMAP_API_KEY"] = api_key

        log(f"Starting CueMap at {selected_url}")
        process = subprocess.Popen(
            arguments,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            env=process_env,
        )
        deadline = time.monotonic() + startup_timeout
        while time.monotonic() < deadline:
            return_code = process.poll()
            if return_code is not None:
                raise RuntimeError(f"CueMap exited before becoming ready (code={return_code})")
            if _inspect_engine(selected_url, api_key) == "cuemap":
                log(f"CueMap is ready at {selected_url}")
                return cls(selected_url, True, process, shutdown_timeout)
            time.sleep(0.1)

        cls(selected_url, True, process, shutdown_timeout).stop()
        raise TimeoutError(f"CueMap did not become ready within {startup_timeout:g}s")

    def stop(self) -> None:
        process = self._process
        self._process = None
        if not self.owned or process is None or process.poll() is not None:
            return
        process.terminate()
        try:
            process.wait(timeout=self._shutdown_timeout)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=self._shutdown_timeout)

    def __enter__(self) -> "EmbeddedCueMap":
        return self

    def __exit__(self, _exc_type, _exc_value, _traceback) -> None:
        self.stop()
