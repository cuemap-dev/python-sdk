# Changelog

All notable changes to the CueMap Python SDK will be documented in this file.

## [0.7.3] - 2026-08-27

### Changed
- Synchronized the SDK patch release and documentation with CueMap Engine v0.7.3.
- Documented compatibility with the engine's Tree-sitter-backed Swift, Dart, Objective-C, and Kotlin ingestion support.
- Changed the default direct-client and embedded-engine port from `8080` to `8735`.

## [0.7.2] - 2026-08-04

### Added
- Added `semantic_mode` (`lexical`, `semantic`, or `hybrid`) and optional `query_embedding` support to both synchronous and asynchronous recall clients.
- Added optional `embedding` and `event_time` support to both memory-write clients, plus one-vector-per-produced-chunk `embeddings` for raw-content ingestion.
- Added synchronous and asynchronous `classify_intent()` helpers for the engine's query/memory intent API.
- Added directory preview, persisted include-path updates, and watch-scope reads to both clients.
- Updated release documentation for the qint8 MiniLM-L3 default and q4 MiniLM-L3 edge profile.

### Removed
- Removed the old embedding-free client description; semantic retrieval is now an explicit, local engine capability rather than an experimental client-side feature.
- Removed CuePack parameters because CuePacks are no longer part of the v0.7.2 Rust API.

## [0.7.1] - 2026-07-17

### Changed
- Synchronized the SDK patch release with CueMap Engine v0.7.1.

## [0.7.0] - 2026-07-06

### Added
- **v0.7 Recall Controls**: Added `query_time`, `trace_timing`, `expansion_depth`, `cuepacks`, parent fusion, ordered reconstruction, evidence coverage, and CueBridge artifact controls.
- **v0.7 Ingestion Controls**: Added `source_key`, `structural_cues`, and segmenter configuration for raw content ingestion.
- **Batch Add API**: Added `add_batch()` and `AsyncCueMap.add_batch()` for `/memories/batch`.
- **Project Artifact APIs**: Added helpers for project artifact summary/reload, project export, and watch directory configuration.
- **Debug Analysis API**: Added `debug_analyze_text()` for v0.7 cue extraction and chunking inspection.

### Changed
- **Memory IDs**: SDK models now accept numeric v0.7 memory IDs.
- **Alias Expansion Default**: `disable_alias_expansion` now defaults to `True`, matching the Rust engine default.
- **Removed Stale Endpoints**: Removed `context_expand()` and `lexicon_synonyms()` because the v0.7 Rust engine no longer exposes those routes.

### Fixed
- Fixed `AsyncCueMap.add()` referencing `disable_temporal_chunking` without accepting it as a parameter.

## [0.6.4] - 2026-03-04

### Added
- **Multi-Hop Recall**: `depth` parameter in recall requests to enable multi-hop associative retrieval.

## [0.6.3] - 2026-02-16

### Added
- **Optional alias expansion**: Added optional alias expansion to the SDK.

## [0.6.1] - 2026-01-21

### Added
- **Context Expansion**: New `context_expand` method to retrieve related concepts from the cue graph.
- **Cloud Backup Management**: New methods (`backup_upload`, `backup_download`, `backup_list`, `backup_delete`) to manage cloud snapshots programmatically.

## [0.6.0] - 2026-01-19

### Added
- **Ingestion API**: New methods `ingest_url`, `ingest_content`, and `ingest_file` for direct content ingestion.
- **Lexicon Management**: New methods (`lexicon_wire`, `lexicon_inspect`, `lexicon_graph`, `lexicon_synonyms`, `lexicon_delete`) for manual control over the engine's associative graph.
- **Job Status**: New `jobs_status()` method to track background ingestion progress.
- **Brain Control Flags**: Added parameters to disable specific brain modules (`disable_pattern_completion`, `disable_salience_bias`, etc.) for deterministic debugging.

### Changed
- **BREAKING**: Refactored `recall` method signature. `query_text` is now the first positional argument, followed by `cues` and `projects`, to prioritize Natural Language Search.
  - Old: `client.recall(cues=["tag"], query_text="search")`
  - New: `client.recall("search", cues=["tag"])`
- **Documentation**: Updated README to reflect the "Brain-Inspired" architecture and new API surface.

## [0.5.0] - 2025-12-27

### Added
- **Asynchronous Client**: Introduced `CueMapAsyncClient` for high-performance non-blocking ingestion and recall.
- **Explainable Recall**: Added `explain: bool` parameter to `recall_weighted` and `recall` methods to retrieve detailed scoring metadata.
- **Advanced Search Parameters**: Support for `min_intersection` and `auto_reinforce` in recall requests.
- **Alias Management**: New methods to add, list, and delete cue aliases for semantic boosting.
- **Grounding Utilities**: Built-in methods to filter and select the most relevant memories from recall results.
- **Multi-tenant Support**: Updated `ProjectConfig` to support project-specific normalization and taxonomy settings.

### Changed
- **Default Weights**: Unified the weighting system to match the Rust engine's continuous gradient scoring.
- **Connection Handling**: Improved retry logic and timeout management for robust communication with the engine.

### Fixed
- **UTF-8 Handling**: Ensured consistent encoding when ingesting non-English or special-character content.
- **JSON Parsing**: Added robust Regex fallback for parsing LLM-generated JSON responses.

---

## [0.4.0] - 2025-11-22
### Added
- Synchronous `CueMapClient` stable release.
- Integration with basic multi-project engine features.
- Performance monitoring hooks.

## [0.3.0] - 2025-10-18
### Added
- Standardized REST-based communication.
- Basic CLI for SDK interaction.
- Unit test suite for core client logic.

## [0.2.0] - 2025-09-10
### Added
- Persistence stubs and local caching.
- Enhanced error reporting and retry strategies.

## [0.1.0] - 2025-08-15
### Added
- Initial Python binding prototype.
- Basic memory ingestion and search methods.

---
*Note: Version 0.7.0 is designed to work with CueMap Rust Engine v0.7.x.*
