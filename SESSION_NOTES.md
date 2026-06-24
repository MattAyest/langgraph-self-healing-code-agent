# Session Notes — Coding Module

## What was built this session

### Architecture (major rework)
Contract-first TDD pipeline replacing the old single-synthesizer approach.

**New flow:**
```
workspace_loader → architect_node → test_writer → contract_verifier → code_writer → static_analyzer → deterministic_verifier → error_distiller → archivist_node
```

**Removed nodes:** `speculative_router`, `local_synthesizer`, `environment_node`

**New nodes:**
- `contract_verifier` — flash model, checks tests match contract before code is written (loop-guarded at 3 retries)

**Key design decisions:**
- Architect outputs `<plan>` and `<contract>` XML blocks parsed into separate state fields (`architectural_plan`, `interface_contract`)
- Test writer receives ONLY the contract — never sees implementation
- Code writer is TDD: receives pre-written tests and must implement to pass them
- Error distiller classifies faults as `implementation` / `tests` / `spec` and routes to `code_writer`, `test_writer`, or `architect_node` accordingly
- Regression threshold: 4 before forcing architect replan

**New state fields:** `interface_contract: str`, `contract_check_count: int`

### Docker sandbox hardening
- Two-phase execution: pip install (network on) → pytest (--network none)
- `--cap-drop ALL`, `--security-opt no-new-privileges`, `--pids-limit 64`, `--memory-swap 512m`, `--ulimit nofile=1024:1024`
- Runs as host user (`--user=$(uid):(gid)`) so volume files stay owned by host user across retries
- `pytest -p no:cacheprovider` to avoid cache write permission issues
- pip install always installs pytest+hypothesis as baseline, then layers requirements.txt on top
- Install failures surface explicitly (stderr captured, non-zero exit checked)
- `.deps` dir cleared and recreated before each verifier run

---

## Test run results (stopped at L3P2)

| Task | Prompt | Status | Loops |
|---|---|---|---|
| L1P1 | Reverse a string | ✅ completed | 1 |
| L1P2 | Prime number check | ✅ completed | 2 |
| L1P3 | Flatten nested list | ✅ completed | 1 |
| L2P1 | Stack data structure | ✅ completed | 1 |
| L2P2 | Word frequency / top N | ✅ completed | 1 |
| L2P3 | Temperature conversion | ✅ completed | 4 ⚠️ |
| L3P1 | Binary search | ✅ completed | 7 ⚠️ |
| L3P2 | LRU cache | ✅ completed | 3 |

### Key observations
- No hard failures (status: `failed`) across 8 tests
- Main friction: Hypothesis strategy generation for constrained inputs (sorted lists, float precision). Test writer repeatedly generates strategies that don't enforce preconditions properly (e.g. unsorted input passed to binary search).
- L3P1 at 7 loops is close to the 10-loop ceiling — Level 4/5 may hit it
- L2P3 temperature conversion: float round-trip precision caused repeated error distiller → test writer cycles

---

## Remaining tests to run (next session)

**Level 3 (remaining):**
- L3P3: `"Write a Python module that parses a CSV string into typed dictionaries with int and float inference"`

**Level 4:**
- L4P1: `"Write a Python module implementing a graph with DFS, BFS, cycle detection, and shortest path"`
- L4P2: `"Write a Python module implementing an expression evaluator supporting +, -, *, /, parentheses, and operator precedence"`
- L4P3: `"Write a Python module implementing a token bucket rate limiter"`

**Level 5:**
- L5P1: `"Write a Python module implementing a min-heap with insert, extract_min, and heapify"`
- L5P2: `"Write a Python module implementing a thread-safe bounded queue with blocking put and get"`
- L5P3: `"Write a Python module implementing run-length encoding and decoding for arbitrary strings"`

---

## Known issues / things to watch
- Loop ceiling of 10 may be hit at Level 4/5 — consider raising or making the architect replan more aggressively
- Hypothesis strategy generation is the weakest link in the test_writer prompt
- `architecture_ledger` is per-task, never shared across tasks (cross-task learning not implemented)
- `local_synthesizer` stub was removed but the node was never implemented
- No `GET /tasks` listing endpoint on the API
