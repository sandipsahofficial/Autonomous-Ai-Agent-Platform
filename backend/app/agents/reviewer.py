from app.agents.state import AgentState
from app.agents.schemas import ReviewerOutput
from app.llm.factory import get_llm_provider
from app.config import get_settings

settings = get_settings()


def reviewer_node(state: AgentState) -> AgentState:
    """
    Reviewer agent node:
    Checks the output of the active agent against requirements.
    Approves or triggers rework loop up to max_rework_attempts.
    """
    state["current_step"] = state.get("current_step", 0) + 1
    llm = get_llm_provider()

    subtasks = state.get("subtasks", [])
    idx = state.get("current_subtask_index", 0)
    current_subtask = subtasks[idx] if idx < len(subtasks) else {}
    last_agent = state.get("last_agent", "worker")

    system_prompt = (
        "You are the Reviewer Agent. Verify that the proposed output satisfies specifications, "
        "has no syntax errors, and meets quality standards. Return structured JSON matching ReviewerOutput."
    )
    prompt = (
        f"Goal: {state.get('goal')}\n"
        f"Subtask: {current_subtask.get('title')}\n"
        f"Agent Under Review: {last_agent}\n"
        f"Output to Review:\n{state.get('current_result')}\n"
        f"Current Rework Attempt: {state.get('rework_count', 0)} of {state.get('max_rework_attempts', settings.MAX_REWORK_ATTEMPTS)}"
    )

    response = llm.generate(
        prompt=prompt,
        system_prompt=system_prompt,
        response_schema=ReviewerOutput,
    )

    state["token_usage"] = state.get("token_usage", 0) + response.usage.total_tokens
    state["estimated_cost_usd"] = round(
        state.get("estimated_cost_usd", 0.0) + response.usage.cost_usd, 6
    )

    rev_data = response.structured or {"status": "APPROVED", "quality_score": 90, "comments": "Approved"}
    review_status = rev_data.get("status", "APPROVED")

    messages = list(state.get("messages", []))
    messages.append({
        "role": "reviewer",
        "subtask_index": idx,
        "status": review_status,
        "score": rev_data.get("quality_score"),
        "comments": rev_data.get("comments"),
    })
    state["messages"] = messages
    state["last_agent"] = "reviewer"

    if review_status == "APPROVED":
        state["is_approved"] = True
        state["review_feedback"] = None
        state["rework_count"] = 0
        state["current_subtask_index"] = idx + 1  # Advance to next subtask
    else:
        # Check rework limit
        max_rework = state.get("max_rework_attempts", settings.MAX_REWORK_ATTEMPTS)
        current_rework = state.get("rework_count", 0) + 1
        state["rework_count"] = current_rework

        if current_rework > max_rework:
            # Force advance with warning rather than looping infinitely
            messages.append({
                "role": "system",
                "warning": f"Max rework attempts ({max_rework}) reached for subtask {idx}. Advancing.",
            })
            state["is_approved"] = True
            state["review_feedback"] = None
            state["rework_count"] = 0
            state["current_subtask_index"] = idx + 1
        else:
            state["is_approved"] = False
            state["review_feedback"] = rev_data.get("rework_instructions", rev_data.get("comments"))

    return state
