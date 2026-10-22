import json
from app.agents.state import AgentState
from app.agents.schemas import CoderOutput
from app.llm.factory import get_llm_provider


def coder_node(state: AgentState) -> AgentState:
    """
    Coder agent node:
    Writes clean, modular code satisfying the subtask specifications.
    Proposes tool execution for file writing or file operations.
    """
    state["current_step"] = state.get("current_step", 0) + 1
    llm = get_llm_provider()

    subtasks = state.get("subtasks", [])
    idx = state.get("current_subtask_index", 0)
    current_subtask = subtasks[idx] if idx < len(subtasks) else {}

    system_prompt = (
        "You are the Coder Agent. Write correct, robust, tested Python code. "
        "Return structured JSON matching CoderOutput."
    )
    prompt = (
        f"Goal: {state.get('goal')}\n"
        f"Active Subtask: {current_subtask.get('title')}\n"
        f"Instructions: {current_subtask.get('description')}\n"
        f"Previous Research: {state.get('current_result', 'N/A')}\n"
        f"Review Feedback (if rework): {state.get('review_feedback', 'None')}"
    )

    response = llm.generate(
        prompt=prompt,
        system_prompt=system_prompt,
        response_schema=CoderOutput,
    )

    state["token_usage"] = state.get("token_usage", 0) + response.usage.total_tokens
    state["estimated_cost_usd"] = round(
        state.get("estimated_cost_usd", 0.0) + response.usage.cost_usd, 6
    )

    state["current_result"] = response.content
    state["last_agent"] = "coder"

    subtask_text = (current_subtask.get("title", "") + " " + current_subtask.get("description", "")).lower()

    # Detect destructive actions like file deletion
    if "delete" in subtask_text or "remove" in subtask_text:
        state["pending_tool_call"] = {
            "tool_name": "file_delete",
            "arguments": {"file_path": "old_cache.tmp"},
        }
    else:
        # Check if code requires saving to file
        coder_data = response.structured or {}
        if coder_data.get("filename") and coder_data.get("code"):
            state["pending_tool_call"] = {
                "tool_name": "file_write",
                "arguments": {
                    "file_path": coder_data.get("filename"),
                    "content": coder_data.get("code"),
                },
            }

    messages = list(state.get("messages", []))
    messages.append({
        "role": "coder",
        "subtask_index": idx,
        "content": response.content,
    })
    state["messages"] = messages

    return state
