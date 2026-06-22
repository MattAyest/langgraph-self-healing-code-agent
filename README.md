# langgraph-self-healing-code-agent

An autonomous, self-healing code generation microservice built with LangGraph and FastAPI.

Submit a natural language prompt and the agent architects a solution, generates Python source and test files, and iteratively verifies its own output inside an isolated Docker sandbox. If tests fail, the system distills the error trace and rewrites the code until all tests pass.

## Key Features

- **State Graph Architecture:** A LangGraph state machine coordinates specialised nodes — architect, synthesizer, static analyzer, verifier, and error distiller — each with a distinct responsibility.
- **Self-Healing Execution Loop:** Generated code is executed in a sandboxed Docker container using `pytest`. Failures are intercepted, condensed into actionable fix instructions, and fed back into the synthesis node. Repeated regressions trigger a full architectural replan.
- **Dual-Model LLM Routing:** Uses `gemini-2.5-pro` for heavy synthesis and architectural planning, and `gemini-2.5-flash` for fast, cheap tasks such as error diagnostics and dependency resolution.
- **Portable Docker-in-Docker:** The verifier spawns sibling containers via the Docker socket. Host paths are resolved automatically at runtime by inspecting the container's own mounts — no machine-specific configuration required.
- **Asynchronous API:** Tasks run in the background. Clients poll for status, current graph node, loop count, and final file output via a REST interface.

## Architecture Flow

1. **Speculative Router:** Evaluates prompt complexity to decide whether a dedicated architectural plan is needed before synthesis begins.
2. **Architect & Environment Node:** Produces a project blueprint and resolves Python dependencies into a `requirements.txt`.
3. **Synthesizer:** Writes the implementation and test suite, structured as `src/` for source files and `tests/` for pytest files.
4. **Static Analyzer:** Parses generated files with Python's `ast` module to catch syntax errors before any code is executed.
5. **Deterministic Verifier:** Writes files to an isolated workspace, mounts it into a `python:3.11-slim` container, and runs `pytest`. Resource limits: 512 MB RAM, 1 CPU, 120 s timeout.
6. **Error Distiller:** Condenses the failure trace into a targeted fix instruction and routes back to the synthesizer. After two consecutive regressions, the architect is forced to produce a new plan.
7. **Archivist:** On success, summarises the winning architecture into a `.architecture.md` ledger in the workspace.

## Prerequisites

- Docker (required — the verifier runs tests inside sibling containers)
- A Google AI API key with access to Gemini 2.5 models

## Getting Started

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/langgraph-self-healing-code-agent.git
   cd langgraph-self-healing-code-agent
   ```

2. Add your API key to `.env`:
   ```
   GOOGLE_API_KEY=your_key_here
   ```

3. Build and start the service:
   ```bash
   docker compose up --build
   ```

## Usage

Submit a code generation request:
```bash
curl -X POST "http://localhost:8000/task" \
     -H "Content-Type: application/json" \
     -d '{"prompt": "Write a Python script that calculates projectile motion and include a pytest suite."}'
```

Poll for status using the returned `task_id`:
```bash
curl -X GET "http://localhost:8000/task/<task_id>"
```

The response tracks `current_node`, `loop_count`, and `regression_count` as the agent works. On completion, `status` becomes `completed` and `result` contains the full verified file manifest. Generated files are also written to `.workspaces/<task_id>/` on the host.
