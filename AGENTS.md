# Project guidance for OpenCode

## Context management

This project is configured to use OpenCode's built-in compaction aggressively. The custom compaction agent keeps only decisions, constraints, code changes, file paths, test results, and unresolved items.

## Semantic search (optional)

The `opencode-rag` MCP server is available but **disabled by default** in `~/.config/opencode/opencode.json`.
When it is enabled, prefer its tools for exploration instead of reading many files at once.
The RAG server auto-starts in Docker and indexes the project at startup.

To enable it, set `"enabled": true` for the `opencode-rag` MCP entry in `~/.config/opencode/opencode.json`.

Available tools:

- `search_codebase(query, n=5)` — find relevant source-code snippets.
- `search_docs(query, n=5)` — find relevant markdown/documentation snippets.
- `index_project(path)` — re-index the project (useful after large changes).
- `rag_status()` — check whether indexing is complete.

Example prompt pattern:

```
@explore search_codebase for how task cancellation works in the FastAPI app
```

Or in the main agent:

```
Use opencode-rag search_codebase to find where the task lifecycle is implemented, then read the relevant files.
```

Only read full files when the RAG results show you need the complete source.

## General rules

- Make minimal, focused changes.
- Follow the existing style in `src/`.
- Run tests or type checks when they exist.
- This is **v0.2** of the pipeline. The v0.1 eight-node design is preserved only in git history — do not reintroduce it.
- If a change affects the API or task lifecycle, update `README.md` (public) and `SESSION_NOTES.md` (private agent guide).
- `SESSION_NOTES.md` is the source of truth for the open-issues tracker and prompt-change log; keep it in sync with `src/`.
- `SESSION_NOTES.md` is now tracked in git, so make sure it stays accurate after any prompt or workflow change.
- If you change prompts in `src/nodes.py`, add a short note to `SESSION_NOTES.md` under the latest session so the next agent knows the prompt was touched.
