import json
import re
from app.agents.state import AgentState
from app.agents.schemas import ExecutorOutput, CoderOutput
from app.llm.factory import get_llm_provider
from app.llm.resilience import generate_with_resilience
from app.services.trace_service import record_execution_event


def executor_node(state: AgentState) -> AgentState:
    """
    Executor / Coder agent node:
    Performs permitted operations through registered safe tools (calculator, JSON validator,
    document inspector, sandbox) and synthesizes code / intermediate deliverables.
    """
    state["current_step"] = state.get("current_step", 0) + 1
    task_id = state.get("task_id", "unknown")
    llm = get_llm_provider()

    subtasks = state.get("subtasks", [])
    idx = state.get("current_subtask_index", 0)
    current_subtask = subtasks[idx] if idx < len(subtasks) else {}
    assigned_role = current_subtask.get("assigned_agent", "executor")
    state["current_stage"] = assigned_role if assigned_role in ("coder", "executor") else "executor"

    if task_id and task_id != "unknown":
        record_execution_event(
            task_id=task_id,
            event_type="AGENT_STARTED",
            message=f"{assigned_role.capitalize()} active on subtask #{idx + 1}: '{current_subtask.get('title')}'",
            agent_name=assigned_role,
            step_index=state["current_step"],
            details={"subtask_index": idx, "title": current_subtask.get("title")},
        )

    system_prompt = (
        "You are the Coder / Executor Agent. Perform calculations, code synthesis, data verification, "
        "and operation execution satisfying the active subtask specifications. "
        "Return structured JSON matching ExecutorOutput or CoderOutput."
    )
    prompt = (
        f"Mission Goal: {state.get('goal')}\n"
        f"Active Subtask: {current_subtask.get('title')}\n"
        f"Instructions: {current_subtask.get('description')}\n"
        f"Prerequisite Research: {state.get('current_result', 'N/A')}\n"
        f"Review Feedback (if rework): {state.get('review_feedback', 'None')}"
    )

    response = generate_with_resilience(
        provider=llm,
        prompt=prompt,
        system_prompt=system_prompt,
        response_schema=CoderOutput,
        max_retries=3,
        task_id=task_id,
        step_index=state["current_step"],
        agent_name="executor",
    )

    state["token_usage"] = state.get("token_usage", 0) + response.usage.total_tokens
    state["estimated_cost_usd"] = round(
        state.get("estimated_cost_usd", 0.0) + response.usage.cost_usd, 6
    )

    state["current_result"] = response.content
    state["last_agent"] = "executor"

    subtask_text = (current_subtask.get("title", "") + " " + current_subtask.get("description", "")).lower()

    # Tool invocation detection based on subtask intent
    if "delete" in subtask_text or "remove" in subtask_text:
        # High-risk destructive action
        state["pending_tool_call"] = {
            "tool_name": "file_delete",
            "arguments": {"file_path": "old_cache.tmp"},
        }
    elif any(kw in subtask_text for kw in ("calculate", "math", "fibonacci", "prime", "arithmetic")):
        # Safe AST Calculator tool
        calc_match = re.search(r"[\d\s\+\-\*\/\(\)\%\^]{3,}", subtask_text)
        expr = calc_match.group(0).strip() if calc_match else "42 * 2"
        state["pending_tool_call"] = {
            "tool_name": "calculator",
            "arguments": {"expression": expr},
        }
    elif "json" in subtask_text or "validate" in subtask_text:
        # JSON Validator tool
        state["pending_tool_call"] = {
            "tool_name": "json_validator",
            "arguments": {"json_string": '{"status": "ok", "code": 200}', "format_output": True},
        }
    else:
        # Check if code output requires saving to workspace file
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
        "role": assigned_role if assigned_role in ("coder", "executor") else "executor",
        "subtask_index": idx,
        "content": response.content,
    })
    state["messages"] = messages

    if task_id and task_id != "unknown":
        record_execution_event(
            task_id=task_id,
            event_type="AGENT_COMPLETED",
            message=f"{assigned_role.capitalize()} completed operations for subtask #{idx + 1}",
            agent_name=assigned_role if assigned_role in ("coder", "executor") else "executor",
            step_index=state["current_step"],
            details={"has_pending_tool": state.get("pending_tool_call") is not None},
        )

    return state
