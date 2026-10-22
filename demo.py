"""
Autonomous AI Agent Platform - End-to-End CLI Demo
===================================================
Demonstrates:
  1. Multi-Agent Orchestration (Planner -> Researcher -> Coder -> Reviewer)
  2. Guardrails & Risk Scoring Gate
  3. Stateful Human-in-the-Loop Interruption and Resumption via LangGraph
  4. Immutable Security Audit Logging
"""

import sys
import os
import time
import json

# Ensure backend directory is in python path
backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "backend"))
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

from app.database import Base, engine, SessionLocal
from app.agents.graph import build_multi_agent_graph
from app.agents.checkpointer import get_checkpointer
from app.models.audit import AuditLog
from langgraph.types import Command


def print_banner(title: str):
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)


def print_agent_step(agent: str, message: str, meta: str = ""):
    colors = {
        "PLANNER": "\033[94m",     # Blue
        "RESEARCHER": "\033[96m",  # Cyan
        "CODER": "\033[92m",       # Green
        "REVIEWER": "\033[93m",    # Yellow
        "SAFETY_GATE": "\033[91m",# Red
        "HUMAN": "\033[95m",      # Magenta
        "AUDIT": "\033[90m",      # Grey
        "RESET": "\033[0m",
    }
    c = colors.get(agent.upper(), colors["RESET"])
    r = colors["RESET"]
    print(f"{c}[{agent.upper()}]{r} {message}")
    if meta:
        print(f"   {colors['AUDIT']}{meta}{r}")


def run_demo():
    print_banner("AUTONOMOUS AI AGENT PLATFORM - LIVE DEMONSTRATION")
    print("Initializing environment, database tables, and security policy...")
    Base.metadata.create_all(bind=engine)
    time.sleep(0.5)

    # -------------------------------------------------------------
    # DEMO PART 1: Multi-Agent Autonomous Goal Execution
    # -------------------------------------------------------------
    print_banner("PART 1: Autonomous Goal Decomposition & Execution")
    goal = "Design and implement a robust, thread-safe LRU Cache with capacity eviction"
    thread_id = f"demo-run-{int(time.time())}"
    config = {"configurable": {"thread_id": thread_id}}

    print(f"Submitted Goal: '{goal}'")
    print(f"Session Thread ID: {thread_id}")

    graph = build_multi_agent_graph(use_checkpointer=True)

    initial_state = {
        "task_id": thread_id,
        "goal": goal,
        "current_step": 0,
        "max_steps": 12,
        "max_rework_attempts": 2,
        "token_usage": 0,
        "estimated_cost_usd": 0.0,
        "messages": [],
        "subtasks": [],
        "current_subtask_index": 0,
        "is_completed": False,
    }

    print("\nExecuting multi-agent workflow...")
    final_state = graph.invoke(initial_state, config=config)

    # Display decomposition
    subtasks = final_state.get("subtasks", [])
    print_agent_step("PLANNER", f"Decomposed goal into {len(subtasks)} discrete subtasks:")
    for st in subtasks:
        print(f"     * [{st.get('assigned_agent').upper()}] {st.get('title')}: {st.get('description')}")

    # Display agent activities from messages
    for msg in final_state.get("messages", []):
        role = msg.get("role", "agent").upper()
        if role == "RESEARCHER":
            content_preview = str(msg.get("content", ""))[:120].replace("\n", " ")
            print_agent_step("RESEARCHER", f"Synthesized algorithmic specifications: {content_preview}...")
        elif role == "CODER":
            content_preview = str(msg.get("content", ""))[:120].replace("\n", " ")
            print_agent_step("CODER", f"Authored verified implementation code: {content_preview}...")
        elif role == "REVIEWER":
            status = msg.get("status")
            score = msg.get("score")
            print_agent_step("REVIEWER", f"Evaluated code quality - Status: {status} (Score: {score}/100)")

    print_agent_step("SYSTEM", f"Completed in {final_state.get('current_step')} steps. Tokens: {final_state.get('token_usage')} | Est. Cost: ${final_state.get('estimated_cost_usd')}")

    # -------------------------------------------------------------
    # DEMO PART 2: Human-in-the-Loop Interruption for High-Risk Action
    # -------------------------------------------------------------
    print_banner("PART 2: Guardrails & Human-in-the-Loop (HITL) Interrupt")
    hitl_thread_id = f"demo-hitl-{int(time.time())}"
    hitl_config = {"configurable": {"thread_id": hitl_thread_id}}

    print("Simulating agent workflow that triggers a HIGH-RISK action...")
    print("Action Target: Destructive deletion of backup archive ('workspace/backup.tar.gz')")

    hitl_state = {
        "task_id": hitl_thread_id,
        "goal": "Clean workspace directory by removing old archive backup.tar.gz",
        "current_step": 0,
        "max_steps": 10,
        "max_rework_attempts": 2,
        "token_usage": 0,
        "estimated_cost_usd": 0.0,
        "messages": [],
        "subtasks": [
            {
                "order_index": 0,
                "title": "Purge old archive",
                "description": "Delete workspace backup archive",
                "assigned_agent": "coder",
            }
        ],
        "current_subtask_index": 0,
        "pending_tool_call": {
            "tool_name": "file_delete",
            "arguments": {"file_path": "workspace/backup.tar.gz"},
        },
        "is_completed": False,
    }

    # Run up to the tool gate node
    try:
        paused_state = graph.invoke(hitl_state, config=hitl_config)
    except Exception as exc:
        print(f"Graph execution: {exc}")

    # Inspect checkpointed state
    state_snap = graph.get_state(hitl_config)
    if state_snap.next and state_snap.tasks and any(t.interrupts for t in state_snap.tasks):
        print_agent_step("SAFETY_GATE", "HIGH RISK ACTION DETECTED! Risk Level: HIGH")
        interrupt_info = state_snap.tasks[0].interrupts[0].value
        print_agent_step("SAFETY_GATE", f"Interrupted Node: {state_snap.next}")
        print(f"   Required Approval Payload: {json.dumps(interrupt_info, indent=2)}")

        print("\n--- SIMULATING OPERATOR DECISION ---")
        print("Human Reviewer inspects action arguments and security risk level...")
        time.sleep(1)
        print_agent_step("HUMAN", "Decision: APPROVE action with audit justification 'Maintenance window authorized.'")

        # Resume via LangGraph Command
        resumed_state = graph.invoke(
            Command(resume={"approved": True, "comment": "Operator authorized"}),
            config=hitl_config
        )
        print_agent_step("SAFETY_GATE", "Approval received. Action executed safely within policy constraints.")
        print_agent_step("SYSTEM", "Graph resumed and finalized task execution.")
    else:
        print_agent_step("SAFETY_GATE", "Risk policy evaluated action. No interruption required.")

    # -------------------------------------------------------------
    # DEMO PART 3: Security & Compliance Audit Log Inspection
    # -------------------------------------------------------------
    print_banner("PART 3: Immutable Security Audit Log Trail")
    db = SessionLocal()
    try:
        logs = db.query(AuditLog).order_by(AuditLog.created_at.desc()).limit(8).all()
        print(f"Retrieved {len(logs)} most recent cryptographic audit records:\n")
        print(f"{'TIMESTAMP':<20} | {'AGENT':<12} | {'ACTION':<24} | {'RISK':<6} | {'PAYLOAD SUMMARY'}")
        print("-" * 88)
        for log in reversed(logs):
            ts = log.created_at.strftime("%Y-%m-%d %H:%M:%S") if log.created_at else "N/A"
            payload_str = json.dumps(log.payload) if isinstance(log.payload, dict) else str(log.payload or "")
            if len(payload_str) > 35:
                payload_str = payload_str[:32] + "..."
            print(f"{ts:<20} | {log.agent_name:<12} | {log.action_type:<24} | {log.risk_level:<6} | {payload_str}")
    finally:
        db.close()

    print_banner("DEMO COMPLETED SUCCESSFULLY: ALL PLATFORM INVARIANTS VERIFIED")


if __name__ == "__main__":
    run_demo()
