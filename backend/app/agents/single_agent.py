import json
from typing import Dict, Any, Literal
from langgraph.graph import StateGraph, END
from app.agents.state import AgentState
from app.llm.factory import get_llm_provider
from app.tools.registry import default_tool_registry
from app.config import get_settings

settings = get_settings()


def agent_node(state: AgentState) -> AgentState:
    """
    Core agent reasoning node:
    - Increments step count.
    - Checks budget safety limits.
    - Calls LLM with structured output tracking.
    - Formulates final output or requests tool execution.
    """
    current_step = state.get("current_step", 0) + 1
    state["current_step"] = current_step

    # Enforce loop limits
    max_steps = state.get("max_steps", settings.MAX_STEPS)
    if current_step > max_steps:
        state["error_message"] = f"Safety Limit Exceeded: Reached max steps ({max_steps})"
        state["is_completed"] = True
        return state

    token_budget = state.get("token_budget", settings.TOKEN_BUDGET)
    if state.get("token_usage", 0) >= token_budget:
        state["error_message"] = f"Budget Exceeded: Reached token budget ({token_budget})"
        state["is_completed"] = True
        return state

    # Query LLM provider
    llm = get_llm_provider()
    system_prompt = (
        "You are an autonomous AI problem-solving agent. "
        "Analyze the user goal, gather data if needed, and produce a clear final output."
    )
    prompt = (
        f"Goal: {state.get('goal')}\n"
        f"Step: {current_step} of {max_steps}\n"
        f"History: {json.dumps(state.get('messages', []))}"
    )

    response = llm.generate(prompt=prompt, system_prompt=system_prompt)

    # Accumulate token and cost accounting
    state["token_usage"] = state.get("token_usage", 0) + response.usage.total_tokens
    state["estimated_cost_usd"] = round(
        state.get("estimated_cost_usd", 0.0) + response.usage.cost_usd, 6
    )

    # Record message in history
    messages = list(state.get("messages", []))
    messages.append({
        "role": "agent",
        "step": current_step,
        "content": response.content,
        "structured": response.structured,
    })
    state["messages"] = messages
    state["last_agent"] = "single_agent"

    # For demonstration of tool integration: if goal mentions "search", propose a search
    goal_lower = state.get("goal", "").lower()
    has_searched = any("tool_output" in m for m in messages)
    if "search" in goal_lower and not has_searched:
        state["pending_tool_call"] = {
            "tool_name": "web_search",
            "arguments": {"query": state.get("goal")},
        }
        state["is_completed"] = False
        return state

    # Mark as completed
    state["final_output"] = response.content
    state["is_completed"] = True
    state["pending_tool_call"] = None
    return state


def tool_executor_node(state: AgentState) -> AgentState:
    """
    Safety-gated tool execution node.
    Every tool call passes through execute_with_safety_gate.
    """
    pending = state.get("pending_tool_call")
    if not pending:
        return state

    tool_name = pending.get("tool_name", "")
    args = pending.get("arguments", {})

    result, risk = default_tool_registry.execute_with_safety_gate(
        tool_name=tool_name,
        arguments=args,
        human_approved=False,
    )

    # Record tool result in messages
    messages = list(state.get("messages", []))
    messages.append({
        "role": "system",
        "tool_output": result.output,
        "error": result.error,
        "risk_level": risk.risk_level.value,
    })
    state["messages"] = messages
    state["pending_tool_call"] = None
    return state


def should_continue(state: AgentState) -> Literal["tool_node", "end"]:
    """
    Conditional edge router:
    Routes to tool node if tool call is pending, else terminates.
    """
    if state.get("is_completed") or state.get("error_message"):
        return "end"

    if state.get("pending_tool_call"):
        return "tool_node"

    return "end"


def build_single_agent_graph() -> StateGraph:
    """
    Assemble and compile the LangGraph workflow.
    """
    workflow = StateGraph(AgentState)

    workflow.add_node("agent", agent_node)
    workflow.add_node("tool_node", tool_executor_node)

    workflow.set_entry_point("agent")

    workflow.add_conditional_edges(
        "agent",
        should_continue,
        {
            "tool_node": "tool_node",
            "end": END,
        },
    )

    # From tool node, return back to agent to synthesize results
    workflow.add_edge("tool_node", "agent")

    return workflow.compile()
