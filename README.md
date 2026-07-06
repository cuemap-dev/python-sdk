# CueMap Python SDK

**High-performance temporal-associative memory store** designed for dynamic contextual retrieval.

## Overview

CueMap implements a **Continuous Gradient Algorithm** optimized for associative data structures:

1.  **Intersection (Context Filter)**: Triangulates relevant memories by overlapping cues
2.  **CuePack-Guided Intent Routing**: Uses compiled deterministic rules to add structural facets and weighted intent cues without runtime model calls.
3.  **Recency & Salience (Signal Dynamics)**: Balances fresh data with salient, high-signal events prioritized by an adaptive impact scoring module.
4.  **Reinforcement (Access-based Learning)**: Frequently accessed memories gain signal strength, remaining highly accessible even as they age.
5.  **Deterministic Facets & Intent Routing**: Extracts synchronous source, evidence, temporal, type, and entity facets, then uses sparse intent cues and reranking during recall.

As of v0.7.0, CueMap's core path is deterministic and embedding-free. GloVe/Ollama cue generation, WordNet/POS expansion, semantic bridges, pattern completion, external lexicon graphs, context expansion/speculation endpoints, and autonomous consolidation have been removed from the core engine.

v0.7.0 also uses numeric per-project memory IDs everywhere. If callers need deterministic upsert/dedupe identity, pass `source_key`; memory IDs remain compact runtime addresses.

Use this SDK to talk to the Rust engine from Python applications.

## Installation

```bash
pip install cuemap
```

## Quick Start

### 1. Start the Engine

```bash
docker run -p 8080:8080 cuemap/engine:latest
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

### v0.7 Recall Controls

CueMap v0.7 adds temporal query intent, CueBridge artifact expansion, and optional reconstruction passes for longer conversational/codebase context.

```python
results = client.recall(
    "what did we decide about auth retries?",
    query_time="2026-07-06",
    ordered_reconstruction="auto",
    evidence_coverage="auto",
    parent_fusion="auto",
    cuepacks=["default"],
    explain=True,
)
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
```

### Advanced Brain Control

Disable specific brain modules for deterministic debugging.

```python
results = client.recall(
    "urgent issue",
    disable_salience_bias=True,
    disable_alias_expansion=True,
    disable_cuebridge_artifacts=True,
)
```

## Async Support

```python
from cuemap import AsyncCueMap

async with AsyncCueMap() as client:
    await client.add("Note")
    await client.recall(cues=["note"])
```

## Performance

- **Write Latency**: ~2ms (O(1) complexity)
- **Read Latency**: ~3ms (P99, 1M memories)

## License

MIT
