import time
from typing import Literal, Optional, Dict, Any
from langgraph.graph import StateGraph, END
from langgraph.types import interrupt
from app.agents.state import AgentState
from app.agents.planner import planner_node
from app.agents.researcher import researcher_node
from app.agents.executor import executor_node
from app.agents.coder import coder_node
from app.agents.reviewer import reviewer_node
from app.agents.finalizer import finalizer_node
from app.agents.checkpointer import get_checkpointer
from app.tools.registry import default_tool_registry
from app.safety.risk_scorer import assess_tool_risk
from app.config import get_settings
from app.services.trace_service import record_execution_event

settings = get_settings()


def router_node(state: AgentState) -> AgentState:
    """
    Evaluates state, checks subtask dependencies, enforces budget caps (steps, tokens, cost),
    and coordinates handoffs between specialized agents.
    """
    subtasks = state.get("subtasks", [])
    idx = state.get("current_subtask_index", 0)
    completed_indices = set(state.get("completed_subtask_indices", []))

    # 1. Budget Bounds Checks (Tokens, Cost, Steps)
    current_step = state.get("current_step", 0)
    max_steps = state.get("max_steps", settings.MAX_STEPS)
    token_usage = state.get("token_usage", 0)
    token_budget = state.get("token_budget", settings.TOKEN_BUDGET)
    cost_usd = state.get("estimated_cost_usd", 0.0)
    cost_budget = state.get("cost_budget_usd", settings.COST_BUDGET_USD)

    if current_step >= max_steps:
        state["error_message"] = f"Execution halted: Exceeded maximum allowed steps ({max_steps})"
        state["is_completed"] = True
        return state

    if token_budget > 0 and token_usage >= token_budget:
        state["error_message"] = f"Budget halted: Token limit reached ({token_usage}/{token_budget} tokens)"
        state["is_completed"] = True
        return state

    if cost_budget > 0 and cost_usd >= cost_budget:
        state["error_message"] = f"Budget halted: Financial limit exceeded (${cost_usd:.4f}/${cost_budget:.2f} USD)"
        state["is_completed"] = True
        return state

    # 2. Dependency Verification for active subtask
    if idx < len(subtasks):
        current_st = subtasks[idx]
        prereqs = current_st.get("dependencies", [])
        unmet_prereqs = [p for p in prereqs if p not in completed_indices]
        if unmet_prereqs:
            # Reorder or prioritize the unmet prerequisite
            for target_p in unmet_prereqs:
                if target_p < len(subtasks):
                    state["current_subtask_index"] = target_p
                    break

    return state


def tool_executor_node(state: AgentState) -> AgentState:
    """
    Unified safety gate & tool execution node.
    Enforces risk assessment, idempotency, human approval pauses, and post-approval re-validation.
    """
    pending = state.get("pending_tool_call")
    if not pending:
        return state

    tool_name = pending.get("tool_name", "")
    args = pending.get("arguments", {})
    task_id = state.get("task_id", "unknown")
    step_index = state.get("current_step", 0)
    idempotency_key = f"{task_id}_{tool_name}_{step_index}"

    state["current_stage"] = "tool_gate"

    # 1. Assess Risk
    risk = assess_tool_risk(tool_name, args)

    human_approved = False
    # 2. Trigger LangGraph Interrupt for HIGH risk actions
    if risk.requires_human_approval:
        approval_payload = {
            "task_id": task_id,
            "tool_name": tool_name,
            "arguments": args,
            "risk_level": risk.risk_level.value,
            "reason": risk.reason,
            "requested_at": time.time(),
        }
        state["pending_approval"] = approval_payload

        if task_id and task_id != "unknown":
            record_execution_event(
                task_id=task_id,
                event_type="APPROVAL_REQUIRED",
                message=f"High-risk action '{tool_name}' paused awaiting operator approval",
                agent_name="tool_gate",
                step_index=step_index,
                status="WARNING",
                details={
                    "tool": tool_name,
                    "risk": risk.risk_level.value,
                    "reason": risk.reason,
                    "arguments": args,
                },
            )

        # Interrupt execution and wait for resume command
        decision: Dict[str, Any] = interrupt(approval_payload)

        # Resumed from human decision
        state["pending_approval"] = None
        if decision.get("approved"):
            human_approved = True
            # Re-validate parameters and risk post-approval to ensure payload was not tampered with
            risk = assess_tool_risk(tool_name, args)
        else:
            rejection_reason = decision.get("feedback", "Rejected by human operator.")
            if task_id and task_id != "unknown":
                record_execution_event(
                    task_id=task_id,
                    event_type="APPROVAL_REJECTED",
                    message=f"Operator rejected action '{tool_name}': {rejection_reason}",
                    agent_name="operator",
                    step_index=step_index,
                    status="WARNING",
                    details={"feedback": rejection_reason},
                )
            messages = list(state.get("messages", []))
            messages.append({
                "role": "system",
                "tool_output": None,
                "error": f"Security Rejection: {rejection_reason}",
                "risk_level": risk.risk_level.value,
            })
            state["messages"] = messages
            state["pending_tool_call"] = None
            return state

    # 3. Execute tool through safety gate with idempotency protection
    result, assessed_risk = default_tool_registry.execute_with_safety_gate(
        tool_name=tool_name,
        arguments=args,
        human_approved=human_approved,
        idempotency_key=idempotency_key,
    )

    if task_id and task_id != "unknown":
        record_execution_event(
            task_id=task_id,
            event_type="TOOL_EXECUTED",
            message=f"Tool '{tool_name}' executed: {'Success' if result.error is None else 'Error'}",
            agent_name="tool_gate",
            step_index=step_index,
            status="SUCCESS" if result.success else "ERROR",
            duration_ms=result.duration_ms,
            idempotency_key=idempotency_key,
            details={
                "tool": tool_name,
                "risk_level": assessed_risk.risk_level.value,
                "has_error": result.error is not None,
                "duration_ms": result.duration_ms,
            },
        )

    # 4. Record output in state history
    messages = list(state.get("messages", []))
    messages.append({
        "role": "system",
        "tool_output": result.output,
        "error": result.error,
        "risk_level": assessed_risk.risk_level.value,
    })
    state["messages"] = messages
    state["pending_tool_call"] = None
    return state


def route_next_action(state: AgentState) -> Literal["researcher", "executor", "coder", "finalizer", "end"]:
    """
    Picks the next stage specialist based on active subtask assignment or routes to finalizer.
    """
    if state.get("is_completed") or state.get("error_message"):
        return "end"

    subtasks = state.get("subtasks", [])
    idx = state.get("current_subtask_index", 0)

    # If all subtasks completed, route to Finalizer stage
    if idx >= len(subtasks) and len(subtasks) > 0:
        return "finalizer"

    if idx >= len(subtasks):
        return "end"

    assigned = subtasks[idx].get("assigned_agent", "researcher")
    if assigned == "executor":
        return "executor"
    elif assigned == "coder":
        return "coder"
    return "researcher"


def route_worker_action(state: AgentState) -> Literal["tool_gate", "reviewer"]:
    """
    If a worker requested a tool, route through safety gate; otherwise advance to reviewer.
    """
    if state.get("pending_tool_call"):
        return "tool_gate"
    return "reviewer"


def route_reviewer_action(state: AgentState) -> Literal["router", "researcher", "executor", "coder"]:
    """
    If reviewer approved, route to router. If rework requested, send back to assigned worker.
    """
    if state.get("is_approved", True):
        return "router"

    subtasks = state.get("subtasks", [])
    idx = state.get("current_subtask_index", 0)
    assigned = subtasks[idx].get("assigned_agent", "researcher") if idx < len(subtasks) else "researcher"

    if assigned == "executor":
        return "executor"
    elif assigned == "coder":
        return "coder"
    return "researcher"


def build_multi_agent_graph(checkpointer=None, use_checkpointer: bool = True):
    """
    Assembles the 5-stage controlled multi-agent workflow:
    Planner -> Router -> [Researcher / Executor / Coder] -> Tool Gate -> Reviewer -> Finalizer.
    Attaches checkpointer for state persistence and human-in-the-loop pause/resume.
    """
    workflow = StateGraph(AgentState)

    workflow.add_node("planner", planner_node)
    workflow.add_node("router", router_node)
    workflow.add_node("researcher", researcher_node)
    workflow.add_node("executor", executor_node)
    workflow.add_node("coder", coder_node)
    workflow.add_node("tool_gate", tool_executor_node)
    workflow.add_node("reviewer", reviewer_node)
    workflow.add_node("finalizer", finalizer_node)

    workflow.set_entry_point("planner")
    workflow.add_edge("planner", "router")

    workflow.add_conditional_edges(
        "router",
        route_next_action,
        {
            "researcher": "researcher",
            "executor": "executor",
            "coder": "coder",
            "finalizer": "finalizer",
            "end": END,
        },
    )

    workflow.add_conditional_edges(
        "researcher",
        route_worker_action,
        {"tool_gate": "tool_gate", "reviewer": "reviewer"},
    )
    workflow.add_conditional_edges(
        "executor",
        route_worker_action,
        {"tool_gate": "tool_gate", "reviewer": "reviewer"},
    )
    workflow.add_conditional_edges(
        "coder",
        route_worker_action,
        {"tool_gate": "tool_gate", "reviewer": "reviewer"},
    )

    workflow.add_edge("tool_gate", "reviewer")

    workflow.add_conditional_edges(
        "reviewer",
        route_reviewer_action,
        {
            "router": "router",
            "researcher": "researcher",
            "executor": "executor",
            "coder": "coder",
        },
    )

    workflow.add_edge("finalizer", END)

    if not use_checkpointer:
        return workflow.compile()

    cp = checkpointer if checkpointer is not None else get_checkpointer()
    return workflow.compile(checkpointer=cp)
