import json
from app.agents.state import AgentState
from app.agents.schemas import ResearcherOutput
from app.llm.factory import get_llm_provider


def researcher_node(state: AgentState) -> AgentState:
    """
    Researcher agent node:
    Gathers factual data, documentation, and references for the active subtask.
    Proposes tool execution for search or file reads.
    """
    state["current_step"] = state.get("current_step", 0) + 1
    llm = get_llm_provider()

    subtasks = state.get("subtasks", [])
    idx = state.get("current_subtask_index", 0)
    current_subtask = subtasks[idx] if idx < len(subtasks) else {}

    system_prompt = (
        "You are the Researcher Agent. Synthesize facts, documentation, and algorithmic "
        "strategies for the assigned subtask. Return structured JSON matching ResearcherOutput."
    )
    prompt = (
        f"Goal: {state.get('goal')}\n"
        f"Active Subtask: {current_subtask.get('title')}\n"
        f"Details: {current_subtask.get('description')}\n"
        f"Review Feedback (if rework): {state.get('review_feedback', 'None')}"
    )

    response = llm.generate(
        prompt=prompt,
        system_prompt=system_prompt,
        response_schema=ResearcherOutput,
    )

    state["token_usage"] = state.get("token_usage", 0) + response.usage.total_tokens
    state["estimated_cost_usd"] = round(
        state.get("estimated_cost_usd", 0.0) + response.usage.cost_usd, 6
    )

    state["current_result"] = response.content
    state["last_agent"] = "researcher"

    subtask_text = (current_subtask.get("title", "") + " " + current_subtask.get("description", "")).lower()
    if "secret" in subtask_text or ".env" in subtask_text:
        state["pending_tool_call"] = {
            "tool_name": "file_read",
            "arguments": {"file_path": "secrets/.env"},
        }
    elif "search" in subtask_text or "lookup" in subtask_text:
        state["pending_tool_call"] = {
            "tool_name": "web_search",
            "arguments": {"query": current_subtask.get("title", state.get("goal"))},
        }

    messages = list(state.get("messages", []))
    messages.append({
        "role": "researcher",
        "subtask_index": idx,
        "content": response.content,
    })
    state["messages"] = messages

    return state
