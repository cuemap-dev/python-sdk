"""Opt-in black-box tests against the real Rust release binary.

Run with ``CUEMAP_E2E=1 pytest -q tests/test_engine_integration.py``.
The normal SDK unit suite stays network-free and does not require a binary.
"""

from __future__ import annotations

import os
import socket
from pathlib import Path

import pytest

from cuemap import AsyncCueMap, CueMap
from cuemap.embedded import EmbeddedCueMap, resolve_cuemap_binary


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
        listener.bind(("127.0.0.1", 0))
        return int(listener.getsockname()[1])


@pytest.fixture(scope="module")
def running_engine(tmp_path_factory):
    if os.environ.get("CUEMAP_E2E") != "1":
        pytest.skip("set CUEMAP_E2E=1 to run real-engine integration tests")
    try:
        workspace_binary = Path(__file__).resolve().parents[2] / "rust_engine" / "target" / "release" / "cuemap"
        binary = os.environ.get("CUEMAP_E2E_BIN")
        if not binary and workspace_binary.is_file():
            binary = str(workspace_binary)
        if not binary:
            binary = resolve_cuemap_binary()
    except FileNotFoundError as exc:
        pytest.skip(str(exc))

    data_dir = tmp_path_factory.mktemp("cuemap-e2e-data")
    runtime = EmbeddedCueMap.start(
        bin_path=binary,
        port=_free_port(),
        startup_timeout=30.0,
        env={
            "CUEMAP_DATA_DIR": str(data_dir),
            "CUEMAP_SEMANTIC_ENCODER_ENABLED": "false",
            "CUEMAP_SNAPSHOT_INTERVAL_SECONDS": "3600",
        },
    )
    try:
        yield runtime
    finally:
        runtime.stop()


def test_sync_sdk_round_trip_and_project_isolation(running_engine):
    project = f"python-sync-e2e-{os.getpid()}"
    client = CueMap(url=running_engine.url, project_id=project)
    try:
        memory_id = client.add(
            "On 2026-08-18 we chose Postgres for the billing migration.",
            cues=["billing", "postgres", "decision"],
            source_key="sdk-e2e:billing-choice",
            event_time=1_755_504_000,
        )
        results = client.recall(
            "What database did we choose for the billing migration?",
            cues=["billing", "postgres"],
            semantic_mode="lexical",
            limit=5,
        )
        assert any(str(result.memory_id) == str(memory_id) for result in results)

        exported = client.export_project(project)
        assert any(str(item["id"]) == str(memory_id) for item in exported["memories"])

        isolated = CueMap(url=running_engine.url, project_id=f"{project}-other")
        try:
            assert isolated.recall(
                "What database did we choose for the billing migration?",
                cues=["billing", "postgres"],
                semantic_mode="lexical",
                limit=5,
            ) == []
        finally:
            isolated.close()
    finally:
        client.close()


@pytest.mark.asyncio
async def test_async_sdk_round_trip(running_engine):
    project = f"python-async-e2e-{os.getpid()}"
    client = AsyncCueMap(url=running_engine.url, project_id=project)
    try:
        memory_id = await client.add(
            "The rollback runbook is stored in docs/rollback.md.",
            cues=["rollback", "runbook"],
            source_key="sdk-e2e:rollback-runbook",
        )
        results = await client.recall(
            "Where is the rollback runbook stored?",
            semantic_mode="lexical",
            limit=5,
        )
        assert any(str(result.memory_id) == str(memory_id) for result in results)
    finally:
        await client.close()
