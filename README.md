<p align="center">
  <img src="https://cuemap.dev/cuemap-logo.PNG" alt="CueMap" width="120">
</p>

<h1 align="center">CueMap Python SDK</h1>

<p align="center">A polished Python client for fast, accurate, and explainable agent memory.</p>

<p align="center">
  <a href="https://pypi.org/project/cuemap/"><img src="https://img.shields.io/pypi/v/cuemap?logo=pypi&logoColor=white" alt="PyPI"></a>
  <a href="https://pypi.org/project/cuemap/"><img src="https://img.shields.io/pypi/pyversions/cuemap?logo=python&logoColor=white" alt="Python versions"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-5e5ce6" alt="License"></a>
  <a href="https://github.com/cuemap-dev/cuemap"><img src="https://img.shields.io/badge/engine-v0.7.3-0f766e" alt="Engine compatibility"></a>
</p>

**High-performance temporal-associative memory store** designed for dynamic contextual retrieval.

## Overview

CueMap uses **temporal-associative retrieval**: lexical and structural candidate generation, with optional semantic reranking. Its main components are:

1.  **Intersection (Context Filter)**: Triangulates relevant memories by overlapping cues
2.  **Local semantic reranking**: Uses bundled qint8 MiniLM-L3 by default, or q4 MiniLM-L3 with the edge profile, for bounded semantic ranking inside the engine.
3.  **Recency & Salience (Signal Dynamics)**: Balances fresh data with salient, high-signal events prioritized by an adaptive impact scoring module.
4.  **Reinforcement (Access-based Learning)**: Frequently accessed memories gain signal strength, remaining highly accessible even as they age.
5.  **Deterministic Facets & Intent Routing**: Extracts synchronous source, evidence, temporal, type, and entity facets, then uses sparse intent cues and reranking during recall.

As of v0.7.3, CueMap keeps deterministic lexical candidate discovery and adds bundled qint8 `paraphrase-MiniLM-L3-v2` for bounded hybrid semantic and intent reranking. The `edge` engine profile uses a q4 build of the same model. No runtime model download is required, and callers can disable the encoder or provide their own vectors.

v0.7.3 also preserves numeric per-project memory IDs everywhere. If callers need deterministic upsert/dedupe identity, pass `source_key`; memory IDs remain compact runtime addresses.

Use this SDK to talk to the Rust engine from Python applications.

## Installation

```bash
pip install cuemap
```

## Quick Start

### 1. Start the Engine

```bash
docker run -p 8735:8735 cuemap/engine:latest
```

### 2. Basic Usage

```python
from cuemap import CueMap

client = CueMap()

# Add a memory with deterministic cue extraction
client.add("The server password is abc123")

# Recall by natural language
results = client.recall("server credentials")
print(results[0].content)
# Output: "The server password is abc123"
```

## Core API

### Add Memory

```python
# Manual cues
client.add(
    "Meeting with John at 3pm",
    cues=["meeting", "john", "calendar"]
)

# Deterministic cues are derived when cues are omitted
client.add("The payments service is down due to a timeout")
```

### Recall Memories

```python
# Natural language search
results = client.recall(
    "payments failure",
    limit=10,
    explain=True # See how the query was expanded
)

print(results[0].explain)
# Shows normalized cues, intent cues, and reranking details.

# Explicit Cue Search
results = client.recall(
    cues=["meeting", "john"],
    min_intersection=2
)
```

### Grounded Recall (Hallucination Guardrails)

Get verifiable context for LLMs with a strict token budget.

```python
response = client.recall_grounded(
    query="Why is the payment failing?",
    token_budget=500
)

print(response["verified_context"])
# [VERIFIED CONTEXT] ...
print(response["proof"])
# Cryptographic proof of context retrieval
```

### Project memory lifecycle

The engine can unload inactive project contexts while keeping their snapshots
on disk. Normal project operations demand-load a project when needed, so the
first request after an unload may take longer. Use the explicit helpers when
you want to control residency:

```python
client.unload_project("older-repository")
client.load_project("older-repository")
client.save_project("older-repository")  # persist without unloading

for project in client.list_projects():
    print(project["project_id"], project["loaded"])
```

Portable projects use the same four operations as the CLI:
`pack_project()`, `load_project_package()`, `push_project()`, and `pull_project()`.
Use `sync_project(project_id, "s3://bucket/team")` for conflict-safe fast-forward sync.

### v0.7.3 Recall Controls

CueMap v0.7.3 adds local semantic query signals alongside temporal query intent and optional reconstruction passes for longer conversational/codebase context.

```python
results = client.recall(
    "what did we decide about auth retries?",
    query_time="2026-07-06",
    ordered_reconstruction="auto",
    evidence_coverage="auto",
    parent_fusion="auto",
    semantic_mode="hybrid",
    explain=True,
)
```

Use `semantic_mode="lexical"` for a semantic-reranker-disabled comparison, `"semantic"` for vector candidate discovery, or `"hybrid"` (the engine default) to rerank lexical candidates. `query_embedding` supplies a precomputed vector when the application owns the embedding provider.

Classify query or memory intent with the same local engine model. Returned scores are ranking signals, not calibrated probabilities:

```python
classification = client.classify_intent(
    "What did we decide about auth retries?",
    target="query",
)
print(classification["primary_intent"], classification["recall_eligible"])
```

### Cloud Backup (v0.6.1)

Manage project snapshots in the cloud (S3, GCS, Azure).

```python
# Upload current project snapshot
client.backup_upload("default")

# Download and restore snapshot
client.backup_download("default")

# List available backups
backups = client.backup_list()
```

### Ingestion (v0.6+)

Ingest content from various sources directly.

```python
# Ingest URL
client.ingest_url("https://example.com/docs")

# Ingest File (PDF, DOCX, etc.)
client.ingest_file("/path/to/document.pdf")

# Ingest Raw Content with v0.7 logical-block chunking
client.ingest_content(
    "Raw text content...",
    filename="notes.md",
    source_key="docs:notes",
    structural_cues=["source_type:docs"],
    segmenter="logical_block",
)
```

When an application chunks content itself, pass exactly one vector per produced chunk with `embeddings=[[...], [...]]`.

Preview and persist a repository ingestion scope:

```python
preview = client.preview_directory("/work/my-app", included_paths=["src"])
client.set_project_watch_dir(
    "repo-my-app",
    "/work/my-app",
    included_paths=["src", "README.md"],
)
scope = client.get_project_watch_dir("repo-my-app")
```

### Lexicon Management (v0.6+)

Inspect and wire the brain's associations manually.

```python
# Inspect a cue's relationships
data = client.lexicon_inspect("service:payment")
print(f"Synonyms: {data['outgoing']}")
print(f"Triggers: {data['incoming']}")

# Manually wire a token to a concept
client.lexicon_wire("stripe", "service:payment")

```

### Job Status (v0.6+)

Check the progress of background ingestion tasks.

```python
status = client.jobs_status()
print(f"Ingested: {status['writes_completed']} / {status['writes_total']}")
print(f"Intent ready: {status.get('intent_ready', False)}")
```

## Async Support

```python
from cuemap import AsyncCueMap

async with AsyncCueMap() as client:
    await client.add("Note")
    await client.recall(cues=["note"])
```

## License

MIT

### Recall previews

The engine's `POST /recall` accepts `response_mode: "preview"` and optional
`preview_chars` (100–2000 UTF-16 code units, default 200). Full content remains
the default. Previews replace each hit's `content` with a leading `preview`,
`content_truncated`, and `content_length`, preserving metadata and ranking.
Use previews for broad discovery, then fetch a selected memory with
`GET /memories/{id}?decoded=true` or read its source. Metadata and diagnostics
are not capped. TypeScript request objects and Python sync/async `recall`
accept these same options; Python returns `RecallPreviewResult` for ungrouped
preview results. The updated engine is required.
