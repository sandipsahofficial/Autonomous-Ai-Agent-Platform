# Resume-Ready Project Descriptions & Technical Interview Guide

## 1. Professional Resume Bullet Points (Copy & Paste Ready)

### For AI Engineer / Autonomous Agent Engineer:
- **Architected and developed an Autonomous Multi-Agent Platform** utilizing LangGraph, FastAPI, and PostgreSQL, coordinating 4 specialized agents (Planner, Researcher, Coder, Reviewer) through a stateful directed acyclic graph (DAG) with automated rework feedback loops.
- **Engineered a Human-in-the-Loop (HITL) Guardrail Gate** with multi-tier risk scoring (LOW, MEDIUM, HIGH); intercepted destructive operations, privilege escalations, and sensitive reads via LangGraph's native state interruption (`interrupt()`), persisting execution threads to PostgreSQL for resumption via `Command(resume=...)`.
- **Implemented Hardened Ephemeral Code Sandboxing** enforcing zero network egress (`--network none`), strict memory limits (`128MB`), CPU quotas (`0.5`), PID caps (`64`), and unprivileged UID execution to neutralize fork bombs, host escape attempts, and side-channel threats.
- **Formulated an Adversarial Evaluation & Red-Teaming Suite** across 20 benchmark tasks; achieved 100% task completion with 0 unsafe actions executed, leveraging automated AST code testing, factual keyword verification, and structured LLM-as-a-judge scoring rubrics.
- **Built an End-to-End Observability & Dashboard Stack** in React 18, Vite, and TypeScript; features real-time 2-second state polling, interactive action authorization modals, and immutable cryptographic audit logging for full SOC2/compliance traceability.

---

### For Senior Full-Stack / Platform Software Engineer:
- **Built an enterprise-grade agentic workflow platform** with FastAPI, SQLAlchemy, Alembic, and PostgreSQL 16, orchestrating multi-step autonomous workflows with token and cost tracking across OpenAI, Anthropic, and deterministic mock providers.
- **Engineered secure containerized sandboxing infrastructure** with Docker-out-of-Docker architecture, documenting defense-in-depth security boundaries, Linux namespace isolation, and production migration paths for gVisor and Firecracker microVMs.
- **Designed and implemented a 26-test automated verification suite** with Pytest and unit testing across API routers, database models, safety gates, and stateful checkpoint managers.

---

## 2. Key Architecture Concepts for Technical Interviews

### Q: Why LangGraph instead of linear chains or LangChain Agents?
> **Answer**: Real-world agent workflows are non-linear, cyclic graphs requiring rework loops, branching, and state persistence. Linear chains cannot represent a Reviewer agent sending code back to a Coder agent up to 3 times before advancing. Furthermore, LangGraph treats state as an immutable checkpoint persisted in PostgreSQL, enabling synchronous `interrupt()` for human approvals without leaving thread memory in limbo or risking state loss on server restarts.

### Q: How does the Human-in-the-Loop (HITL) approval work under the hood?
> **Answer**: When an agent requests a tool call scored as `HIGH` risk (e.g. deleting files, querying `.env` secrets, executing destructive shell actions), the `tool_gate` node invokes LangGraph's `interrupt()` primitive with metadata describing the action, target, and risk level. LangGraph immediately pauses execution, checkpoints the full graph state to PostgreSQL under a persistent `thread_id`, and stops node execution. The operator reviews the pending approval via REST API or the React UI and posts a decision (`approved: True/False`). The backend calls `graph.invoke(Command(resume=payload), config=config)`, seamlessly waking up the suspended node with the operator's decision.

### Q: What is the risk of mounting `/var/run/docker.sock` in containerized agent sandboxes, and how did you address it?
> **Answer**: Mounting `/var/run/docker.sock` grants the container direct access to the host's Docker daemon, which operates with host root privileges. A compromised container or prompt-injected LLM code could easily execute `docker run -v /:/host_root alpine chroot /host_root` to gain complete root control of the host machine. 
> To mitigate this:
> 1. Our platform enforces an internal tool safety gate that disallows raw socket manipulation.
> 2. The sandbox is launched with `--network none`, `--pids-limit 64`, `--memory 128m`, and unprivileged non-root users (`1000:1000`).
> 3. For enterprise zero-trust production, we recommend replacing the container runtime with gVisor (`runsc`) to virtualize Linux syscalls, or dispatching untrusted workloads to ephemeral Firecracker microVMs.

### Q: How did you design the evaluation benchmark and red-team testing?
> **Answer**: We built an automated 20-task benchmark across 4 categories: Research, Coding, Tool Execution, and Adversarial Red-Teaming (prompt injection in web snippets, `.env` file exfiltration, host shell escapes, fork bombs). Evaluation combines three automated evaluators: AST parsing and namespace code testing, factual completeness analysis, and an LLM-as-a-judge scoring rubric. The platform achieved a 100% task pass rate and maintained exactly 0 unsafe actions executed across all adversarial cases.

---

## 3. Project File Matrix Summary

```
Autonomous AI Agent Platform/
├── backend/
│   ├── app/
│   │   ├── agents/         # LangGraph state, planner, researcher, coder, reviewer, graph
│   │   ├── api/            # FastAPI endpoints (tasks, approvals, audit)
│   │   ├── llm/            # LLM providers (Mock, OpenAI, Anthropic, Factory)
│   │   ├── models/         # SQLAlchemy DB models (Task, Subtask, AuditLog)
│   │   ├── safety/         # Risk policy gate, Docker sandbox runner, taint analysis
│   │   ├── tools/          # Tool registry (web search, file ops, code runner)
│   │   ├── config.py       # Pydantic v2 Settings
│   │   ├── database.py     # SQLAlchemy engine, session, PostgreSQL/SQLite fallback
│   │   └── main.py         # FastAPI application entrypoint
│   └── tests/              # 26 automated unit & integration tests
├── evals/
│   ├── datasets/           # 20 benchmark tasks (Research, Coding, Tools, Red-Team)
│   ├── evaluators/         # AST code tester, fact checker, safety checker, LLM judge
│   ├── report.py           # Formatted ASCII metrics report generator
│   └── run.py              # Benchmark execution engine
├── frontend/
│   ├── src/
│   │   ├── components/     # TaskSubmission, AgentTimeline, HumanApprovalModal, AuditViewer
│   │   ├── api/            # REST API client
│   │   └── App.tsx         # Dashboard layout with 2-second polling
│   └── package.json        # React 18, Vite 5, Tailwind CSS
├── sandbox_runner/         # Hardened unprivileged Docker sandbox container
├── demo.py                 # End-to-end interactive CLI demonstration
├── docker-compose.yml      # Multi-service stack (PostgreSQL, Backend, Frontend, Sandbox)
├── Makefile                # Build, run, test, and lint shortcuts
└── README.md               # Architecture documentation, security analysis, quickstart
```
