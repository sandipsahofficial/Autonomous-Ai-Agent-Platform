from typing import Literal, Optional, Dict, Any
from langgraph.graph import StateGraph, END
from langgraph.types import interrupt
from app.agents.state import AgentState
from app.agents.planner import planner_node
from app.agents.researcher import researcher_node
from app.agents.coder import coder_node
from app.agents.reviewer import reviewer_node
from app.agents.checkpointer import get_checkpointer
from app.tools.registry import default_tool_registry
from app.safety.risk_scorer import assess_tool_risk
from app.config import get_settings

settings = get_settings()


def router_node(state: AgentState) -> AgentState:
    """
    Evaluates state and checks overall termination conditions.
    """
    subtasks = state.get("subtasks", [])
    idx = state.get("current_subtask_index", 0)

    # Check if all subtasks are finished
    if idx >= len(subtasks) and len(subtasks) > 0:
        state["is_completed"] = True
        state["final_output"] = (
            f"Successfully completed all {len(subtasks)} subtasks for goal: '{state.get('goal')}'\n"
            f"Last Result:\n{state.get('current_result')}"
        )

    # Check step limits
    if state.get("current_step", 0) >= state.get("max_steps", settings.MAX_STEPS):
        state["error_message"] = f"Exceeded max steps ({settings.MAX_STEPS})"
        state["is_completed"] = True

    return state


def tool_executor_node(state: AgentState) -> AgentState:
    """
    Unified safety gate & tool execution node.
    If an action is classified as HIGH risk, interrupts workflow until human approval is received.
    """
    pending = state.get("pending_tool_call")
    if not pending:
        return state

    tool_name = pending.get("tool_name", "")
    args = pending.get("arguments", {})

    # 1. Assess Risk
    risk = assess_tool_risk(tool_name, args)

    human_approved = False
    # 2. Trigger LangGraph Interrupt for HIGH risk actions
    if risk.requires_human_approval:
        approval_payload = {
            "task_id": state.get("task_id", "unknown"),
            "tool_name": tool_name,
            "arguments": args,
            "risk_level": risk.risk_level.value,
            "reason": risk.reason,
        }
        state["pending_approval"] = approval_payload

        # Interrupt execution and wait for resume command
        decision: Dict[str, Any] = interrupt(approval_payload)

        # Resumed from human decision
        state["pending_approval"] = None
        if decision.get("approved"):
            human_approved = True
        else:
            rejection_reason = decision.get("feedback", "Rejected by human operator.")
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

    # 3. Execute tool through safety gate
    result, assessed_risk = default_tool_registry.execute_with_safety_gate(
        tool_name=tool_name,
        arguments=args,
        human_approved=human_approved,
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


def route_next_action(state: AgentState) -> Literal["researcher", "coder", "end"]:
    """
    Picks the next specialist based on the current subtask's assigned_agent.
    """
    if state.get("is_completed") or state.get("error_message"):
        return "end"

    subtasks = state.get("subtasks", [])
    idx = state.get("current_subtask_index", 0)

    if idx >= len(subtasks):
        return "end"

    assigned = subtasks[idx].get("assigned_agent", "researcher")
    if assigned == "coder":
        return "coder"
    return "researcher"


def route_worker_action(state: AgentState) -> Literal["tool_gate", "reviewer"]:
    """
    If a worker requested a tool, route through safety gate, otherwise to reviewer.
    """
    if state.get("pending_tool_call"):
        return "tool_gate"
    return "reviewer"


def route_reviewer_action(state: AgentState) -> Literal["router", "researcher", "coder"]:
    """
    If reviewer approved, route to router. If rework requested, send back to assigned worker.
    """
    if state.get("is_approved", True):
        return "router"

    subtasks = state.get("subtasks", [])
    idx = state.get("current_subtask_index", 0)
    assigned = subtasks[idx].get("assigned_agent", "researcher") if idx < len(subtasks) else "researcher"

    if assigned == "coder":
        return "coder"
    return "researcher"


def build_multi_agent_graph(checkpointer=None, use_checkpointer: bool = True):
    """
    Assembles the complete Planner -> Router -> Worker -> Tool Gate -> Reviewer graph.
    Attaches checkpointer for state persistence and human-in-the-loop pause/resume.
    """
    workflow = StateGraph(AgentState)

    workflow.add_node("planner", planner_node)
    workflow.add_node("router", router_node)
    workflow.add_node("researcher", researcher_node)
    workflow.add_node("coder", coder_node)
    workflow.add_node("tool_gate", tool_executor_node)
    workflow.add_node("reviewer", reviewer_node)

    workflow.set_entry_point("planner")
    workflow.add_edge("planner", "router")

    workflow.add_conditional_edges(
        "router",
        route_next_action,
        {
            "researcher": "researcher",
            "coder": "coder",
            "end": END,
        },
    )

    workflow.add_conditional_edges(
        "researcher",
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
            "coder": "coder",
        },
    )

    if not use_checkpointer:
        return workflow.compile()

    cp = checkpointer if checkpointer is not None else get_checkpointer()
    return workflow.compile(checkpointer=cp)
