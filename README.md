# CueMap Python SDK

**High-performance temporal-associative memory store** that mimics the brain's recall mechanism.

## Overview

CueMap implements a **Continuous Gradient Algorithm** inspired by biological memory:

1.  **Intersection (Context Filter)**: Triangulates relevant memories by overlapping cues
2.  **Pattern Completion (Associative Recall)**: Automatically infers missing cues from co-occurrence history, enabling recall from partial inputs.
3.  **Recency & Salience (Signal Dynamics)**: Balances fresh data with salient, high-signal events prioritized by the Amygdala-inspired salience module.
4.  **Reinforcement (Hebbian Learning)**: Frequently accessed memories gain signal strength, staying "front of mind".
5.  **Autonomous Consolidation**: Periodically merges overlapping memories into summaries, mimicking systems consolidation.

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

# Add a memory (auto-cue generation by default using internal Semantic Engine)
client.add("The server password is abc123")

# Recall by natural language (resolves via Lexicon)
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

# Auto-cues (Semantic Engine)
client.add("The payments service is down due to a timeout")
```

### Recall Memories

```python
# Natural Language Search (Brain-Inspired)
results = client.recall(
    "payments failure",
    limit=10,
    explain=True # See how the query was expanded
)

print(results[0].explain)
# Shows normalized cues, expanded synonyms, etc.

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

### Context Expansion (v0.6.1)

Explore related concepts from the cue graph to expand a user's query.

```python
response = client.context_expand("server hung 137", limit=5)
# {
#   "query_cues": ["server", "hung", "137"],
#   "expansions": [
#     { "term": "out_of_memory", "score": 25.0, "co_occurrence_count": 12 },
#     { "term": "SIGKILL", "score": 22.0, "co_occurrence_count": 8 }
#   ]
# }
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

# Ingest Raw Content
client.ingest_content("Raw text content...", filename="notes.txt")
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

# Get synonyms via WordNet
synonyms = client.lexicon_synonyms("payment")
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
    disable_pattern_completion=True,    # No associative inference
    disable_salience_bias=True,         # No emotional weighting
    disable_systems_consolidation=True, # No gist summaries
    disable_temporal_chunking=True      # No episodic grouping
)
```

## Async Support

```python
from cuemap import AsyncCueMap

async with AsyncCueMap() as client:
    await client.add("Note")
    await client.recall(["note"])
```

## Performance

- **Write Latency**: ~2ms (O(1) complexity)
- **Read Latency**: ~5-10ms (Raw vs Smart Recall)

## License

MIT
