import subprocess
from pathlib import Path
from unittest.mock import Mock

import pytest
from cuemap import embedded


@pytest.mark.parametrize("system,machine,expected", [
    ("Windows", "AMD64", "win32-x64"), ("Linux", "aarch64", "linux-arm64"),
    ("Linux", "x86_64", "linux-x64"), ("Darwin", "arm64", "darwin-arm64"),
    ("Darwin", "x86_64", "darwin-x64"),
])
def test_native_platform_names(monkeypatch, system, machine, expected):
    monkeypatch.setattr(embedded.platform, "system", lambda: system)
    monkeypatch.setattr(embedded.platform, "machine", lambda: machine)
    assert embedded._platform_package() == "@cuemap-dev/engine-" + expected


def test_unsupported_architecture_is_not_misidentified(monkeypatch):
    monkeypatch.setattr(embedded.platform, "machine", lambda: "riscv64")
    with pytest.raises(RuntimeError, match="Unsupported"):
        embedded._platform_package()


def test_windows_wrapper_launch_and_auth_environment(monkeypatch, tmp_path):
    wrapper = tmp_path / "cuemap"
    wrapper.write_text("// wrapper")
    monkeypatch.setattr(embedded.platform, "system", lambda: "Windows")
    monkeypatch.setattr(embedded.shutil, "which", lambda name: "node.exe")
    monkeypatch.setattr(embedded, "_inspect_engine", Mock(side_effect=["closed", "cuemap"]))
    process = Mock()
    process.poll.return_value = None
    popen = Mock(return_value=process)
    monkeypatch.setattr(embedded.subprocess, "Popen", popen)
    engine = embedded.EmbeddedCueMap.start(bin_path=str(wrapper), api_key="test-secret", env={"CUEMAP_HOST": "0.0.0.0"})
    assert popen.call_args.args[0][:2] == ["node.exe", str(wrapper)]
    assert popen.call_args.kwargs["env"]["CUEMAP_API_KEY"] == "test-secret"
    assert popen.call_args.kwargs["env"]["CUEMAP_HOST"] == "127.0.0.1"
    engine.stop()
    process.wait.assert_called_once()


def test_startup_timeout_reaps_process(monkeypatch, tmp_path):
    executable = tmp_path / "cuemap.exe"
    executable.write_text("")
    monkeypatch.setattr(embedded, "_inspect_engine", lambda *args: "closed")
    process = Mock()
    process.poll.return_value = None
    process.wait.side_effect = [subprocess.TimeoutExpired("cuemap", 0), 0]
    monkeypatch.setattr(embedded.subprocess, "Popen", Mock(return_value=process))
    with pytest.raises(TimeoutError):
        embedded.EmbeddedCueMap.start(bin_path=str(executable), startup_timeout=0, shutdown_timeout=0)
    process.terminate.assert_called_once()
    process.kill.assert_called_once()
    assert process.wait.call_count == 2


def test_windows_global_npm_layout_resolves_native_executable(monkeypatch, tmp_path):
    npm_dir = tmp_path / 'npm'
    npm_cli = npm_dir / 'node_modules' / 'npm' / 'bin' / 'npm-cli.js'
    npm_cli.parent.mkdir(parents=True)
    npm_cli.write_text('// npm CLI')
    package_root = tmp_path / 'global' / 'node_modules'
    native = package_root / '@cuemap-dev' / 'engine-win32-x64' / 'bin' / 'cuemap-native.exe'
    native.parent.mkdir(parents=True)
    native.write_bytes(b'test fixture')
    monkeypatch.delenv('CUEMAP_BIN', raising=False)
    monkeypatch.setattr(embedded.platform, 'system', lambda: 'Windows')
    monkeypatch.setattr(embedded.platform, 'machine', lambda: 'AMD64')
    monkeypatch.setattr(embedded.shutil, 'which', lambda name: {
        'cuemap': str(npm_dir / 'cuemap.cmd'), 'npm': str(npm_dir / 'npm.cmd'), 'node': 'node.exe',
    }.get(name))
    run = Mock(return_value=Mock(stdout=str(package_root)))
    monkeypatch.setattr(embedded.subprocess, 'run', run)
    assert embedded.resolve_cuemap_binary() == str(native)
    assert run.call_args.args[0] == ['node.exe', str(npm_cli), 'root', '--global']
