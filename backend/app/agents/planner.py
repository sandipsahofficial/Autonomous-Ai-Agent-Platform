import json
from app.agents.state import AgentState
from app.agents.schemas import PlannerOutput
from app.llm.factory import get_llm_provider


def planner_node(state: AgentState) -> AgentState:
    """
    Planner agent node:
    Breaks down the user goal into structured, ordered subtasks.
    If subtasks are already present in state, preserves them.
    """
    state["current_step"] = state.get("current_step", 0) + 1

    # Preserve pre-existing subtasks if supplied (e.g. injected plans or resumed tasks)
    if state.get("subtasks") and len(state["subtasks"]) > 0:
        state["current_subtask_index"] = state.get("current_subtask_index", 0)
        state["rework_count"] = state.get("rework_count", 0)
        state["last_agent"] = "planner"
        return state

    llm = get_llm_provider()

    system_prompt = (
        "You are the Lead Planner Agent. Break down the user's overarching goal into "
        "ordered, discrete subtasks assigned to either 'researcher' or 'coder'. "
        "Return structured JSON matching PlannerOutput."
    )
    prompt = f"Goal to accomplish: {state.get('goal')}"

    response = llm.generate(
        prompt=prompt,
        system_prompt=system_prompt,
        response_schema=PlannerOutput,
    )

    state["token_usage"] = state.get("token_usage", 0) + response.usage.total_tokens
    state["estimated_cost_usd"] = round(
        state.get("estimated_cost_usd", 0.0) + response.usage.cost_usd, 6
    )

    plan_data = response.structured or {
        "plan_summary": "Standard plan",
        "subtasks": [
            {
                "order_index": 0,
                "title": "Information Research",
                "description": "Gather technical facts.",
                "assigned_agent": "researcher",
            },
            {
                "order_index": 1,
                "title": "Code Implementation",
                "description": "Write code implementation.",
                "assigned_agent": "coder",
            },
        ],
    }

    state["subtasks"] = plan_data.get("subtasks", [])
    state["current_subtask_index"] = 0
    state["rework_count"] = 0
    state["last_agent"] = "planner"

    messages = list(state.get("messages", []))
    messages.append({
        "role": "planner",
        "content": response.content,
        "plan_summary": plan_data.get("plan_summary"),
        "subtask_count": len(state["subtasks"]),
    })
    state["messages"] = messages

    return state
