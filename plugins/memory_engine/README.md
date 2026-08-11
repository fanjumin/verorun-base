# Agent Memory & Self-Evolution (memory_engine)

Hierarchical agent memory with vector retrieval, Reflexion-based self-evolution and prompt metrics for VeroRun's 9-role Agent Matrix.

## Features

- **Layered Memory**: Working memory + long-term vector memory stored in independent `memory_engine` PostgreSQL schema.
- **Reflexion Engine**: Automatic self-reflection on failed/low-confidence tasks, generating structured lessons.
- **Prompt Evolution**: Daily metrics aggregation across prompt versions, admin-approved optimization suggestions.
- **Evolution Ring**: Interactive SVG visualization of the evolution lifecycle with round playback and phase drill-down.
- **Privacy-first**: Per-user Opt-in, PII filtering, independent schema isolation.

## Requirements

- VeroRun >= 0.10.0
- PostgreSQL 16 with pgvector extension (optional; degrades gracefully to keyword search)
- AI Engine kernel patches A/B/C (see `docs/memory_engine-plugin-dev-doc.md` §10)

## Configuration

See the plugin settings page in Admin → Plugins → Agent Memory for all configurable options, including:
- Embedding model selection
- Memory retrieval top-K
- Extraction/reflexion toggles
- Retention and per-owner caps

## Admin Pages

- `/admin/memory` — Memory browser (search, view, delete)
- Evolution Ring tab — Interactive ring visualization of evolution rounds

## Architecture

All business logic resides in `plugins/memory_engine/`. The AI engine kernel requires only three low-impact patches:
1. `UnifiedLLM.get_embedding()` — embedding capability
2. `EventName.AGENT_TASK_COMPLETED` — task completion event
3. `before_prompt_resolve` filter hook

See the full development document for details: `F:\Sites\审计与方案\memory_engine-plugin-dev-doc.md`
