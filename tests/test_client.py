import json

import httpx
import pytest

from cuemap import CueMap
from cuemap import embedded


def test_add_sends_original_event_time():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen.update(json.loads(request.content))
        return httpx.Response(200, json={"id": 7})

    client = CueMap(project_id="hermes-main")
    client.client.close()
    client.client = httpx.Client(
        base_url="http://localhost:8735",
        transport=httpx.MockTransport(handler),
    )

    memory_id = client.add(
        "Historical message",
        source_key="hermes:session-1:message-1",
        event_time=1_704_067_200.25,
    )

    assert memory_id == 7
    assert seen["source_key"] == "hermes:session-1:message-1"
    assert seen["event_time"] == 1_704_067_200.25


def test_recall_sends_v072_semantic_controls():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen.update(json.loads(request.content))
        return httpx.Response(200, json={"results": []})

    client = CueMap(project_id="semantic-test")
    client.client.close()
    client.client = httpx.Client(
        base_url="http://localhost:8735",
        transport=httpx.MockTransport(handler),
    )

    assert client.recall(
        "What did we decide about auth retries?",
        semantic_mode="hybrid",
        query_embedding=[0.1, 0.2, 0.3],
    ) == []
    assert seen["semantic_mode"] == "hybrid"
    assert seen["query_embedding"] == [0.1, 0.2, 0.3]


def test_intent_classification_matches_engine_contract():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["path"] = request.url.path
        seen.update(json.loads(request.content))
        return httpx.Response(200, json={
            "primary_intent": "decision",
            "scores": {"decision": 0.8},
            "top_intents": ["decision"],
            "top_score": 0.8,
            "margin": 0.2,
            "confidence_weight": 0.9,
            "recall_eligible": True,
            "recall_action": "recall",
            "memory_eligible": True,
            "model_version": "test",
            "taxonomy_version": "cuekey-intents-v2",
        })

    client = CueMap(project_id="intent-test")
    client.client.close()
    client.client = httpx.Client(
        base_url="http://localhost:8735",
        transport=httpx.MockTransport(handler),
    )

    result = client.classify_intent("What did we decide?", target="query")
    assert seen == {
        "path": "/intent/classify",
        "text": "What did we decide?",
        "target": "query",
    }
    assert result["primary_intent"] == "decision"


def test_repository_scope_and_chunk_embeddings_match_engine_schema():
    requests = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append({
            "path": request.url.path,
            "method": request.method,
            "body": json.loads(request.content) if request.content else None,
        })
        return httpx.Response(200, json={"status": "ok"})

    client = CueMap(project_id="repo-test")
    client.client.close()
    client.client = httpx.Client(
        base_url="http://localhost:8735",
        transport=httpx.MockTransport(handler),
    )

    client.preview_directory("/work/app", included_paths=["src"])
    client.set_project_watch_dir(
        "repo-test",
        "/work/app",
        ignored_patterns=["dist/**"],
        ignored_extensions=["map"],
        included_paths=["src", "README.md"],
    )
    client.get_project_watch_dir("repo-test")
    client.ingest_content(
        "First chunk. Second chunk.",
        embeddings=[[0.1, 0.2], [0.3, 0.4]],
    )

    assert requests[0]["body"]["included_paths"] == ["src"]
    assert requests[1]["body"]["included_paths"] == ["src", "README.md"]
    assert requests[2]["method"] == "GET"
    assert requests[3]["body"]["embeddings"] == [[0.1, 0.2], [0.3, 0.4]]


def test_project_lifecycle_methods_match_engine_routes():
    requests = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append((request.method, request.url.path))
        return httpx.Response(200, json={"status": "ok", "loaded": request.url.path.endswith("/load")})

    client = CueMap(project_id="lifecycle-test")
    client.client.close()
    client.client = httpx.Client(
        base_url="http://localhost:8735",
        transport=httpx.MockTransport(handler),
    )

    assert client.load_project("repo-one")["loaded"] is True
    assert client.save_project("repo-one")["status"] == "ok"
    assert client.unload_project("repo-one")["loaded"] is False
    assert requests == [
        ("POST", "/projects/repo-one/load"),
        ("POST", "/projects/repo-one/save"),
        ("POST", "/projects/repo-one/unload"),
    ]


@pytest.mark.asyncio
async def test_async_project_lifecycle_methods_match_engine_routes():
    requests = []

    async def handler(request: httpx.Request) -> httpx.Response:
        requests.append((request.method, request.url.path))
        return httpx.Response(200, json={"status": "ok"})

    from cuemap import AsyncCueMap

    client = AsyncCueMap(project_id="async-lifecycle-test")
    await client.client.aclose()
    client.client = httpx.AsyncClient(
        base_url="http://localhost:8735",
        transport=httpx.MockTransport(handler),
    )

    await client.load_project("repo-two")
    await client.save_project("repo-two")
    await client.unload_project("repo-two")
    await client.close()

    assert requests == [
        ("POST", "/projects/repo-two/load"),
        ("POST", "/projects/repo-two/save"),
        ("POST", "/projects/repo-two/unload"),
    ]


def test_project_package_methods_match_engine_routes():
    requests = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append((request.method, request.url.path, request.content))
        if request.url.path.endswith("/pack"):
            return httpx.Response(200, content=b"CUEMAP01package")
        return httpx.Response(200, json={"status": "ok"})

    client = CueMap(project_id="package-test")
    client.client.close()
    client.client = httpx.Client(
        base_url="http://localhost:8735",
        transport=httpx.MockTransport(handler),
    )

    package = client.pack_project("repo-package")
    assert package == b"CUEMAP01package"
    client.load_project_package(package)
    client.push_project("repo-package", "s3://bucket/team/")
    client.pull_project("s3://bucket/team/repo-package.cuemap")
    client.sync_project("repo-package", "s3://bucket/team-sync")

    assert [(method, path) for method, path, _ in requests] == [
        ("POST", "/projects/repo-package/pack"),
        ("POST", "/projects/load"),
        ("POST", "/projects/repo-package/push"),
        ("POST", "/projects/pull"),
        ("POST", "/projects/repo-package/sync"),
    ]
    assert requests[1][2] == package
    assert json.loads(requests[2][2]) == {"destination": "s3://bucket/team/"}
    assert json.loads(requests[3][2]) == {"source": "s3://bucket/team/repo-package.cuemap"}
    assert json.loads(requests[4][2]) == {"remote": "s3://bucket/team-sync"}


@pytest.mark.asyncio
async def test_async_project_package_methods_match_engine_routes():
    requests = []

    async def handler(request: httpx.Request) -> httpx.Response:
        requests.append((request.method, request.url.path))
        if request.url.path.endswith("/pack"):
            return httpx.Response(200, content=b"CUEMAP01async")
        return httpx.Response(200, json={"status": "ok"})

    from cuemap import AsyncCueMap

    client = AsyncCueMap(project_id="async-package-test")
    await client.client.aclose()
    client.client = httpx.AsyncClient(
        base_url="http://localhost:8735",
        transport=httpx.MockTransport(handler),
    )

    package = await client.pack_project("repo-package-async")
    await client.load_project_package(package)
    await client.push_project("repo-package-async", "s3://bucket/team/")
    await client.pull_project("s3://bucket/team/repo-package-async.cuemap")
    await client.sync_project("repo-package-async", "s3://bucket/team-sync")
    await client.close()

    assert requests == [
        ("POST", "/projects/repo-package-async/pack"),
        ("POST", "/projects/load"),
        ("POST", "/projects/repo-package-async/push"),
        ("POST", "/projects/pull"),
        ("POST", "/projects/repo-package-async/sync"),
    ]


def test_embedded_runtime_attaches_without_owning_process(monkeypatch):
    monkeypatch.setattr(embedded, "_inspect_engine", lambda _url, _api_key=None: "cuemap")

    runtime = embedded.EmbeddedCueMap.start(url="http://localhost:8735/")

    assert runtime.url == "http://localhost:8735"
    assert runtime.owned is False


def test_explicit_binary_resolution(tmp_path):
    executable = tmp_path / "cuemap"
    executable.write_text("test")

    assert embedded.resolve_cuemap_binary(str(executable)) == str(executable)


def test_preview_recall_sync_and_async():
    import asyncio
    from cuemap import AsyncCueMap, RecallPreviewResult

    def handler(request):
        payload = json.loads(request.content)
        assert payload['response_mode'] == 'preview'
        assert payload['preview_chars'] == 100
        return httpx.Response(200, json={'response_mode': 'preview', 'results': [{
            'memory_id': 1, 'preview': 'excerpt', 'content_truncated': True,
            'content_length': 500, 'score': 1, 'intersection_count': 1,
            'recency_score': 1, 'reinforcement_score': 0,
        }]})

    client = CueMap()
    client.client.close()
    client.client = httpx.Client(base_url='http://localhost:8735', transport=httpx.MockTransport(handler))
    try:
        hit = client.recall('discovery', response_mode='preview', preview_chars=100)[0]
        assert isinstance(hit, RecallPreviewResult)
        assert hit.preview == 'excerpt' and hit.content is None
    finally:
        client.client.close()

    async def check():
        client = AsyncCueMap()
        await client.client.aclose()
        client.client = httpx.AsyncClient(base_url='http://localhost:8735', transport=httpx.MockTransport(handler))
        try:
            hit = (await client.recall('discovery', response_mode='preview', preview_chars=100))[0]
            assert isinstance(hit, RecallPreviewResult)
            assert hit.content_truncated and hit.content is None
        finally:
            await client.client.aclose()
    asyncio.run(check())
