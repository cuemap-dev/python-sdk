# Changelog

All notable changes to the CueMap Python SDK will be documented in this file.

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
*Note: This version is designed to work with CueMap Rust Engine v0.6.x.*
