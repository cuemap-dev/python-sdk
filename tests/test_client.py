import json

import httpx

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
        base_url="http://localhost:8080",
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
        base_url="http://localhost:8080",
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
        base_url="http://localhost:8080",
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
        base_url="http://localhost:8080",
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


def test_embedded_runtime_attaches_without_owning_process(monkeypatch):
    monkeypatch.setattr(embedded, "_inspect_engine", lambda _url, _api_key=None: "cuemap")

    runtime = embedded.EmbeddedCueMap.start(url="http://localhost:8080/")

    assert runtime.url == "http://localhost:8080"
    assert runtime.owned is False


def test_explicit_binary_resolution(tmp_path):
    executable = tmp_path / "cuemap"
    executable.write_text("test")

    assert embedded.resolve_cuemap_binary(str(executable)) == str(executable)
