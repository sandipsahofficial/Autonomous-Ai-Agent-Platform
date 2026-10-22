# MESH (Autonomous AI Agent Platform) - System Audit Report

**Date of Audit**: October 22, 2026  
**Auditor**: Senior AI Systems Engineer  
**Audit Scope**: End-to-end inspection of frontend UI/UX, multi-agent orchestrator, safety gate, tool sandbox, REST APIs, persistence layer, and evaluation benchmarks.

---

## 1. Project Architecture

The platform is structured into four primary layers:

```
+---------------------------------------------------------------------------------------+
|                               FRONTEND PRESENTATION LAYER                             |
|  React 18 + Vite 5 + TypeScript (Dashboard: Overview, Traces, Approvals, Audit Logs)   |
|  Live polling: GET /api/v1/tasks, GET /api/v1/audit-logs every 2s                     |
+-------------------------------------------+-------------------------------------------+
                                            | HTTP Proxy (/api -> http://127.0.0.1:8001)
+-------------------------------------------v-------------------------------------------+
|                                BACKEND ORCHESTRATION LAYER                            |
|  FastAPI (Port 8001) + Pydantic v2 + BackgroundTasks runner                           |
|  Routers: /api/v1/tasks, /api/v1/tasks/{id}/pending-approval, /api/v1/audit-logs      |
+-------------------------------------------+-------------------------------------------+
                                            |
+-------------------------------------------v-------------------------------------------+
|                              MULTI-AGENT WORKFLOW (LangGraph)                         |
|  Planner -> Router -> (Researcher | Coder) -> Tool Gate (Risk Scoring) -> Reviewer   |
|  State persistence via LangGraph BaseCheckpointSaver (MemorySaver / PostgresSaver)   |
+---------------------+---------------------+---------------------+---------------------+
                      |                     |                     |
+---------------------v-----+ +-------------v-------+ +-----------v---------------------+
|      TOOL REGISTRY        | |   CONTAINER SANDBOX | |      PERSISTENCE LAYER          |
| Web Search (Taint Wrapper)| | Docker 3.11-alpine  | | PostgreSQL 16 (Docker Compose)  |
| File Ops (Workspace Safe) | | --network none      | | SQLite dev.db (Local dev)       |
| Code Runner (Sandbox)     | | --memory 128m       | | SQLAlchemy + Alembic Migrations |
+---------------------------+ +---------------------+ +---------------------------------+
```

---

## 2. Working Features (Verified by Code & Tests)

| Feature | Verification Method | Notes |
| :--- | :--- | :--- |
| **Multi-Agent Compilation & State Graph** | `backend/tests/test_multi_agent_graph.py` (26/26 passed) | Planner, Researcher, Coder, and Reviewer execute in a cyclical DAG up to `max_rework_attempts = 3`. |
| **Tool Risk Classification** | `backend/tests/test_tools_and_safety.py` | Accurately classifies actions into `LOW` (read-only), `MEDIUM` (file write), and `HIGH` (delete, `.env`, shell). |
| **Path Traversal Protection** | `backend/app/tools/file_ops.py` | Strictly locks filesystem access inside `WORKSPACE_ROOT` via `os.path.commonpath()`. |
| **Hardened Ephemeral Docker Sandbox** | `backend/app/safety/sandbox.py` | Subprocess executes with `--network none`, `--memory 128m`, `--pids-limit 64`, unprivileged UID `1000:1000`, and fallback to isolated `py -I`. |
| **Prompt Injection Taint Analysis** | `backend/app/safety/taint.py` | Wraps external inputs in `<untrusted_external_data>` tags and strips known injection markers. |
| **Task Creation & Background Execution** | Verified via live API call `POST /api/v1/tasks` | Creates task, runs background graph, populates subtasks, and marks status `COMPLETED`. |
| **Audit Logging API & Viewer** | `GET /api/v1/audit-logs`, `AuditLogViewer.tsx` | Immutable audit trail recorded in database; frontend allows risk filtering and payload JSON inspection. |
| **LangGraph Checkpoint Resumption** | `backend/tests/test_human_approval.py`, `demo.py` | Pauses at `interrupt()` on high-risk tool call, resumes on `Command(resume=...)`. |
| **Comprehensive Benchmark Suite** | `evals/run.py` (20/20 PASS) | 100% pass rate across Research, Coding, Tool Execution, and Red-Team safety attacks. 0 unsafe actions executed. |

---

## 3. Incomplete Features & Disconnected Controls

| Element | Location | Current State / Defect |
| :--- | :--- | :--- |
| **Sidebar Navigation Tabs** | `frontend/src/App.tsx` | Clicking **`Agent fleet`**, **`Knowledge`**, or **`Settings`** renders an empty screen (no conditional view rendered). |
| **Approval Queue Mock Actions** | `MeshApprovalQueue.tsx` | The 3 static items (`Finance Agent`, `Success Agent`, `Ops Agent`) trigger a browser `alert()` instead of an API call. |
| **Inspect Traces Button** | `MeshMissionGraph.tsx` | Button has no `onClick` handler (does not navigate to the traces tab). |
| **Agent Fleet Table Controls** | `MeshAgentFleetTable.tsx` | `+ New agent` opens the generic mission modal; row `⋯` buttons do nothing. |
| **Top Bar Search & Bell** | `frontend/src/App.tsx` | Search bar has an input state `searchQuery` but does not filter missions or agents; notification bell has no dropdown. |
| **Guardrails Tab** | `frontend/src/App.tsx` | Renders `AgentTimeline` rather than a guardrail policy dashboard or active tool risk inspector. |
| **Task Interruption in Background Runner** | `backend/app/api/tasks.py` | In `run_agent_task_background`, if a task halts at `interrupt()`, the function currently sets `t.status = TaskStatus.COMPLETED` rather than `TaskStatus.WAITING_APPROVAL`. |
| **Global Pending Approvals Endpoint** | `backend/app/api/approvals.py` | There is only `GET /tasks/{id}/pending-approval` for a single task; no endpoint exists to list *all* currently pending approvals across all tasks. |

---

## 4. Mock Data Locations

The following components currently use hardcoded/mock data rather than live database records:

1. **`MeshStatCards.tsx`** (`frontend/src/components/MeshStatCards.tsx`):
   - Default props: `activeCount = 12`, `successRate = 98.4%`, `avgCost = $0.42`, `pendingApprovals = 3`.
   - Sparkline SVG polylines are hardcoded coordinate points.
2. **`MeshApprovalQueue.tsx`** (`frontend/src/components/MeshApprovalQueue.tsx`):
   - `staticItems`: Finance Agent ($2,450 refund), Success Agent (renewal proposal), Ops Agent (.env update).
3. **`MeshAgentFleetTable.tsx`** (`frontend/src/components/MeshAgentFleetTable.tsx`):
   - `agents`: 4 static rows (`Research Scout`, `Finance Guard`, `Success Hub`, `Coder Sentinel`) with hardcoded run counts and costs.
4. **`MeshMobileShowcase.tsx`** (`frontend/src/components/MeshMobileShowcase.tsx`):
   - 3 mobile screen cards at the bottom of the page display hardcoded demo metrics (`Run #R-2841`, Helio Labs renewal, etc.).
5. **`MeshMissionGraph.tsx`** (`frontend/src/components/MeshMissionGraph.tsx`):
   - Default nodes: `Planner`, `Research`, `CRM`, `Risk`, `Writer` with static coordinate positions and hardcoded descriptions.

---

## 5. Backend & API Status

* **Host / Port**: `http://127.0.0.1:8001` (Relocated from 8000 to prevent collision with external services).
* **Endpoints Registered**:
  * `GET /health`: Operational (returns model and cluster metadata).
  * `POST /api/v1/tasks`: Operational (creates task and launches background execution).
  * `GET /api/v1/tasks`: Operational (returns task list with pagination).
  * `GET /api/v1/tasks/{id}`: Operational (returns task details and subtasks).
  * `DELETE /api/v1/tasks/{id}`: Operational (deletes task and associated subtasks).
  * `GET /api/v1/tasks/{id}/pending-approval`: Operational (queries LangGraph snapshot).
  * `POST /api/v1/tasks/{id}/approve`: Operational (resumes interrupted graph with decision).
  * `GET /api/v1/audit-logs`: Operational (queries `AuditLog` table with risk filters).
* **Missing Endpoints**:
  * `GET /api/v1/approvals/pending` (to fetch all tasks waiting for approval in one call).
  * `GET /api/v1/metrics/fleet` (to serve aggregate KPIs: total runs, success rate, cost).
  * `GET /api/v1/guardrails/policies` (to serve active tool risk thresholds and sandbox configurations).

---

## 6. AI Integration Status

* **Provider Abstraction** (`backend/app/llm/`):
  * `MockLLMProvider`: **Fully integrated and active**. Provides deterministic, schema-compliant JSON for testing without API keys or costs.
  * `OpenAILLMProvider`: **Integrated**. Directly calls `https://api.openai.com/v1/chat/completions` via `httpx` with JSON schema enforcement and token/cost tracking.
  * `ClaudeLLMProvider`: **Integrated**. Implements Anthropic Messages API.
  * `factory.py`: Dynamically selects provider based on `LLM_PROVIDER` in `.env`.
* **Current Operational Mode**: Defaults to `LLM_PROVIDER=mock`. To switch to real OpenAI models, set `LLM_PROVIDER=openai` and specify `OPENAI_API_KEY` in `.env`.

---

## 7. Database Status

* **Engines Supported**:
  * SQLite: Local development (`dev.db`).
  * PostgreSQL 16: Containerized deployment (`docker-compose.yml`).
* **Active Tables**:
  * `tasks`: Stores task ID, goal, status, steps, token usage, cost, final output, error message.
  * `subtasks`: Stores task ID, order index, title, description, assigned agent, status, result.
  * `audit_logs`: Stores audit ID, task ID, agent name, action type, risk level, payload, timestamp.
* **Database Deficiencies**:
  * **Traces / Intermediate Messages**: Full multi-agent conversation messages (`messages` list) are kept in memory by LangGraph but are **not** persisted in a dedicated database table (`messages` or `execution_traces`). Once the server restarts, detailed step-by-step reasoning logs cannot be reloaded from SQL.
  * **Local Checkpointing**: On SQLite, checkpoints rely on in-memory `MemorySaver()`. Persistent state checkpoints are only written to disk when connected to PostgreSQL (`PostgresSaver`).

---

## 8. Security Review Findings

1. **Unrestricted Network / Command Execution**:
   - Docker sandbox has `--network none` and `--read-only` rootfs. Secure by default.
   - Fallback subprocess runner uses `py -I` with strict timeouts.
2. **Path Traversal**:
   - `_resolve_safe_path` enforces that resolved paths reside inside `WORKSPACE_ROOT`. Secure against `../../` attacks.
3. **Authentication & Authorization**:
   - **CRITICAL FINDING**: All API routes are completely unauthenticated (`CORSMiddleware` has `allow_origins=["*"]`). Anyone on the local network can dispatch tasks, approve high-risk actions, or query audit logs.
4. **Secret Management**:
   - No production API keys are hardcoded in git. `.env.example` and `.env` use blank placeholder keys.

---

## 9. Recommended Implementation Order (Phased Remediation)

To bring the platform from demo-ready to production-grade while preserving the existing UI:

### Phase A: Core Pipeline Fixes (High Priority)
1. **Fix Background Approval Handling**:
   - In `backend/app/api/tasks.py`, inspect `state_snapshot.tasks` for interrupts. If interrupted, set `task.status = TaskStatus.WAITING_APPROVAL` instead of `COMPLETED`.
2. **Add Global Pending Approvals API**:
   - Implement `GET /api/v1/approvals/pending` in `backend/app/api/approvals.py` to return all tasks currently in `WAITING_APPROVAL`.
   - Wire `MeshApprovalQueue.tsx` to display real database approvals, replacing the browser `alert()` mock handlers.

### Phase B: Frontend Navigation & Views (Medium Priority)
3. **Connect Missing Sidebar Views**:
   - In `frontend/src/App.tsx`, build view containers for `fleet` (dedicated Agent Fleet view), `guardrails` (Guardrail & Sandbox Policy inspector), and `settings` (LLM Provider & Budget configuration).
4. **Wire Top Controls**:
   - Connect the top `searchQuery` to filter the tasks and agent fleet table in real time.
   - Connect the `Inspect traces ↗` button in `MeshMissionGraph.tsx` to automatically switch to the `runs` tab.

### Phase C: Trace Persistence & Real Metrics (Medium Priority)
5. **Database Trace Model**:
   - Add a `TaskTrace` or `TaskMessage` table in `backend/app/models/task.py` to persist intermediate agent thought chains, code outputs, and reviewer feedback.
6. **Dynamic Fleet KPIs**:
   - Replace hardcoded stat card defaults in `MeshStatCards.tsx` with live aggregates calculated from the `tasks` table (total runs, average cost, success rate).

### Phase D: API Authentication & Hardening (Final Hardening)
7. **Basic API Key / Bearer Auth**:
   - Add a lightweight API key header dependency (`X-API-Key` or Bearer token) to secure endpoints against unauthorized access.
