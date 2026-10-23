from app.agents.state import AgentState
from app.agents.schemas import ResearcherOutput
from app.llm.factory import get_llm_provider
from app.llm.resilience import generate_with_resilience
from app.services.trace_service import record_execution_event


def researcher_node(state: AgentState) -> AgentState:
    """
    Researcher agent node:
    Gathers factual data, documentation, and references for the active subtask.
    Proposes authorized tool execution (search, document inspection, summarization).
    """
    state["current_step"] = state.get("current_step", 0) + 1
    state["current_stage"] = "researcher"
    task_id = state.get("task_id", "unknown")
    llm = get_llm_provider()

    subtasks = state.get("subtasks", [])
    idx = state.get("current_subtask_index", 0)
    current_subtask = subtasks[idx] if idx < len(subtasks) else {}

    if task_id and task_id != "unknown":
        record_execution_event(
            task_id=task_id,
            event_type="AGENT_STARTED",
            message=f"Researcher active on subtask #{idx + 1}: '{current_subtask.get('title')}'",
            agent_name="researcher",
            step_index=state["current_step"],
            details={"subtask_index": idx, "title": current_subtask.get("title")},
        )

    system_prompt = (
        "You are the Researcher Agent. Synthesize verified facts, documentation, and references "
        "for the assigned subtask. Return structured JSON matching ResearcherOutput."
    )
    prompt = (
        f"Mission Goal: {state.get('goal')}\n"
        f"Active Subtask: {current_subtask.get('title')}\n"
        f"Details: {current_subtask.get('description')}\n"
        f"Review Feedback (if rework): {state.get('review_feedback', 'None')}"
    )

    response = generate_with_resilience(
        provider=llm,
        prompt=prompt,
        system_prompt=system_prompt,
        response_schema=ResearcherOutput,
        max_retries=3,
        task_id=task_id,
        step_index=state["current_step"],
        agent_name="researcher",
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
    elif "doc" in subtask_text or "inspect" in subtask_text:
        state["pending_tool_call"] = {
            "tool_name": "doc_inspector",
            "arguments": {"relative_path": "."},
        }
    elif "summariz" in subtask_text:
        state["pending_tool_call"] = {
            "tool_name": "text_summarizer",
            "arguments": {"text": prompt, "max_sentences": 2},
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

    if task_id and task_id != "unknown":
        record_execution_event(
            task_id=task_id,
            event_type="AGENT_COMPLETED",
            message=f"Researcher completed analysis for subtask #{idx + 1}",
            agent_name="researcher",
            step_index=state["current_step"],
            details={"has_pending_tool": state.get("pending_tool_call") is not None},
        )

    return state
