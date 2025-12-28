# CueMap: Redis for AI Agents

**High-performance, temporal-associative memory store.**

You give us the cues, we give you the right memory at the right time.

## Why CueMap?

Redis doesn't auto-serialize your data. It doesn't guess what you mean. It just stores keys and values **blazing fast**.

CueMap is the same philosophy for AI agent memory:
- ✅ **You control the cues** (tags)
- ✅ **We handle the speed** (sub-millisecond)
- ✅ **No magic** (predictable behavior)
- ✅ **No dependencies** (5KB SDK)

## Installation

```bash
pip install cuemap
```

That's it. No ML models. No transformers. Just pure speed.

## Quick Start

### 1. Start the Engine

```bash
docker run -p 8080:8080 cuemap/engine:latest
```

### 2. Use the SDK

```python
from cuemap import CueMap

client = CueMap()

# Add a memory with cues
client.add(
    "The server password is abc123",
    cues=["server", "password", "credentials"]
)

# Recall by cues
results = client.recall(["server", "password"])
print(results[0].content)
# Output: "The server password is abc123"
```

## Core API

### Add Memory

```python
memory_id = client.add(
    content="Meeting with John at 3pm",
    cues=["meeting", "john", "calendar", "today"]
)
```

### Recall Memories

```python
# OR logic (default): matches any cue
results = client.recall(
    cues=["meeting", "john"],
    limit=10
)

for result in results:
    print(f"{result.content} (score: {result.score})")

# AND logic: requires all cues to match
results = client.recall(
    cues=["meeting", "john"],
    min_intersection=2  # Both cues must match
)

# Cross-domain query (multi-tenant mode)
results = client.recall(
    cues=["urgent"],
    projects=["sales", "support", "engineering"]
)
```

### Reinforce Memory

```python
# Make a memory more accessible
client.reinforce(memory_id, cues=["important", "urgent"])
```

## How It Works

### Temporal-Associative Retrieval

CueMap uses **Iterative Deepening Intersection**:

1. **Intersection**: Memories matching multiple cues rank higher
2. **Recency**: Recent memories are more accessible
3. **Reinforcement**: Frequently accessed memories stay "front of mind"

```python
# Add memories
client.add("Pizza recipe", cues=["food", "italian"])
client.add("Pasta recipe", cues=["food", "italian"])
client.add("Sushi recipe", cues=["food", "japanese"])

# Query with multiple cues
results = client.recall(["food", "italian"])
# Returns: Pizza and Pasta (both match 2 cues)
# Sushi is filtered out (only matches 1 cue)
```

### Performance (~1M memories)

- **Write P99**: 0.33ms
- **Read P99**: 0.37ms
- **Throughput**: 2,900+ ops/sec
- **Accuracy**: 100% (validated on 120 test scenarios)

## Recipes

### Recipe 1: Use with OpenAI

```python
from cuemap import CueMap
import openai

client = CueMap()

def store_with_ai_tags(content: str):
    # Let OpenAI extract the cues
    response = openai.chat.completions.create(
        model="gpt-4",
        messages=[{
            "role": "system",
            "content": "Extract 3-5 search tags from the text. Return as JSON array."
        }, {
            "role": "user",
            "content": content
        }]
    )
    
    cues = response.choices[0].message.content  # ["tag1", "tag2", ...]
    
    # Store in CueMap
    return client.add(content, cues=cues)

# Usage
store_with_ai_tags("I need to buy groceries this weekend")
# OpenAI extracts: ["shopping", "groceries", "weekend", "todo"]
```

### Recipe 2: Use with LangChain

```python
from cuemap import CueMap
from langchain.memory import BaseMemory

class CueMapMemory(BaseMemory):
    def __init__(self, cue_extractor):
        self.client = CueMap()
        self.extract_cues = cue_extractor
    
    def save_context(self, inputs, outputs):
        context = f"User: {inputs['input']}\nAI: {outputs['output']}"
        cues = self.extract_cues(context)
        self.client.add(context, cues=cues)
    
    def load_memory_variables(self, inputs):
        cues = self.extract_cues(inputs['input'])
        results = self.client.recall(cues, limit=5)
        return {"history": "\n".join([r.content for r in results])}
```

### Recipe 3: Manual Cues (Production)

```python
# For production: explicit, predictable cues
client.add(
    "Deploy command: kubectl apply -f deployment.yaml",
    cues=["deployment", "kubernetes", "commands", "devops"]
)

client.add(
    "API endpoint: https://api.example.com/v1/users",
    cues=["api", "endpoint", "users", "documentation"]
)

# Query with specific cues
client.recall(["deployment", "kubernetes"])
client.recall(["api", "users"])
```

## Running the Engine

CueMap requires a running engine. Choose your deployment:

### Option 1: Docker (Recommended)

```bash
docker run -p 8080:8080 cuemap/engine:latest
```

### Option 2: From Source

```bash
git clone https://github.com/cuemap-dev/engine
cd engine
cargo build --release
./target/release/cuemap-rust --port 8080
```

## Configuration

### Connect to Engine

```python
# Default (localhost)
client = CueMap()

# Custom URL
client = CueMap(url="http://your-server:8080")

# With authentication
client = CueMap(
    url="http://your-server:8080",
    api_key="your-secret-key"
)
```

### Multi-tenancy

```python
# Use project isolation
client = CueMap(
    url="http://your-server:8080",
    project_id="my-project"
)
```

### Async Support

```python
from cuemap import AsyncCueMap

async with AsyncCueMap() as client:
    await client.add("Note", cues=["work"])
    await client.recall(["work"])

### Natural Language Recall (Deterministic)

Use the built-in Lexicon to resolve human language into canonical cues.

```python
# Resolved via Lexicon: "payment" -> "service:payment", "timeout" -> "error:timeout"
results = client.recall(query_text="payment timeout")
```

### Alias Management (Manual Control)

Tweak the engine's deterministic mapping directly.

```python
# Add a manual alias
client.add_alias(from_cue="pay", to_cue="service:payment", weight=0.9)

# Merge multiple terms into one canonical cue
client.merge_aliases(cues=["failed", "error", "bug"], to_cue="status:error")

# List aliases
aliases = client.get_aliases(cue="pay")
```

### Advanced Brain Control (Safety Audit)

For peak determinism or specific recall strategies, you can disable brain-inspired features per-request.

```python
# 1. Disable Pattern Completion (Strict matching only, no associative inference)
results = client.recall(
    cues=["urgent"],
    disable_pattern_completion=True
)

# 2. Disable Salience Bias (Ignore "importance" signals, use pure recency/frequency)
results = client.recall(
    query_text="server logs",
    disable_salience_bias=True
)

# 3. Disable Systems Consolidation (Ignore summarized "gist" memories)
results = client.recall(
    query_text="project history",
    disable_systems_consolidation=True
)

# 4. Disable Temporal Chunking (Stop automatic episode creation at write-time)
client.add(
    "Standalone event",
    cues=["event"],
    disable_temporal_chunking=True
)
```

### Explainable Recall

See how the query was normalized and expanded.

```python
results = client.recall(
    query_text="payment failed",
    explain=True
)

# Access explanation
print(results[0].explain)
```

## Grounding & Token Budgeting (v0.5)

CueMap v0.5 introduces the **Relevance Compression Engine** to prevent LLM hallucinations by providing a "Hallucination Guardrail".

### Grounded Recall

Get the most relevant context formatted specifically for LLM prompts, within a strict token budget.

```python
results = client.recall_grounded(
    query="Why is the payment failing?",
    token_budget=500,  # Strict limit
    limit=10
)

print(results["verified_context"])
# Output: [VERIFIED CONTEXT] (1) Fact... Rules: Use only context...
```

### CueMapGroundingRetriever (Middleware)

A tiny library for easy integration into LangChain, LlamaIndex, or custom pipelines.

```python
from cuemap import CueMapGroundingRetriever

retriever = CueMapGroundingRetriever()
result = retriever.retrieve_grounded(
    query_text="Why did the database fail?",
    token_budget=300
)

# context ready for prompt injection
prompt = f"Answer this query: {query}\n\n{result['verified_context_block']}"
```
```

## Philosophy

### What CueMap Does

✅ **Fast storage** - Sub-millisecond retrieval
✅ **Temporal ordering** - Recent memories prioritized
✅ **Intersection scoring** - Multi-cue matching
✅ **Reinforcement** - Move-to-front operation

### What CueMap Doesn't Do

❌ **Auto-tagging** - You provide the cues
❌ **Semantic search** - Use your own embeddings
❌ **LLM integration** - Bring your own model
❌ **Magic** - Explicit and predictable

## Why This Approach?

**Redis Philosophy**: Don't guess what the user wants. Provide primitives. Let them build.

**CueMap Philosophy**: Don't auto-extract cues. Don't auto-embed. Just store and retrieve **fast**.

**Benefits**:
- 🚀 **5KB SDK** (vs 500MB with ML models)
- ⚡ **Instant install** (1 second vs 5 minutes)
- 🎯 **Predictable** (no ML black boxes)
- 🔧 **Flexible** (works with any LLM/embedding model)

## Comparison

| Feature | CueMap | Vector DBs |
|---------|--------|------------|
| **Speed** | 0.37ms P99 | 200-500ms |
| **SDK Size** | 5KB | 500MB+ |
| **Dependencies** | 2 | 50+ |
| **Install Time** | 1 sec | 5 min |
| **Cue Control** | Explicit | Auto (black box) |
| **Temporal** | ✅ Built-in | ❌ None |

## Documentation

- [Engine Repository](https://github.com/cuemap-dev/engine)
- [SDKs Repository](https://github.com/cuemap-dev/sdks)
- [Examples](https://github.com/cuemap-dev/sdks/tree/main/python/examples)

## License

MIT
