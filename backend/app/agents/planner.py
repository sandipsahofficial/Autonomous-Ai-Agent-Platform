import json
from app.agents.state import AgentState
from app.agents.schemas import PlannerOutput
from app.llm.factory import get_llm_provider
from app.llm.resilience import generate_with_resilience
from app.database import SessionLocal
from app.services.memory_service import MemoryService, format_memories_as_untrusted_context
from app.services.trace_service import record_execution_event


def planner_node(state: AgentState) -> AgentState:
    """
    Planner agent node:
    Searches historical memories for relevant strategies, breaks down the user goal
    into discrete verifiable subtasks with dependencies, and assigns specialists.
    """
    state["current_step"] = state.get("current_step", 0) + 1
    state["current_stage"] = "planner"
    task_id = state.get("task_id", "unknown")
    user_id = state.get("user_id", "sandip_sah")
    goal = state.get("goal", "")

    # Preserve pre-existing subtasks if supplied (e.g. injected plans or resumed tasks)
    if state.get("subtasks") and len(state["subtasks"]) > 0:
        state["current_subtask_index"] = state.get("current_subtask_index", 0)
        state["rework_count"] = state.get("rework_count", 0)
        state["last_agent"] = "planner"
        return state

    # Step 1: Memory Search before planning
    memory_context = ""
    try:
        db = SessionLocal()
        try:
            memories = MemoryService.search_memories(
                db=db,
                user_id=user_id,
                query=goal,
                limit=3,
            )
            if memories:
                memory_context = format_memories_as_untrusted_context(memories)
                state["retrieved_memories"] = [
                    {"id": m.id, "key": m.key, "type": m.memory_type} for m in memories
                ]
                if task_id and task_id != "unknown":
                    record_execution_event(
                        task_id=task_id,
                        event_type="MEMORY_READ",
                        message=f"Retrieved {len(memories)} relevant historical memory item(s)",
                        agent_name="planner",
                        step_index=state["current_step"],
                        details={"memory_keys": [m.key for m in memories]},
                    )
        finally:
            db.close()
    except Exception as mem_err:
        memory_context = ""

    # Step 2: Invoke LLM with resilience and schema validation
    llm = get_llm_provider()

    system_prompt = (
        "You are the Lead Planner Agent. Decompose the mission goal into small, verifiable, "
        "ordered subtasks assigned to 'researcher' (for gathering knowledge) or 'executor' "
        "(for performing calculations, JSON processing, document checks, or operations). "
        "Each subtask can declare prerequisite 'dependencies' by order_index.\n"
        "Return structured JSON matching PlannerOutput."
    )

    prompt = f"Mission Goal: {goal}"
    if memory_context:
        prompt = f"{memory_context}\n\n{prompt}"

    response = generate_with_resilience(
        provider=llm,
        prompt=prompt,
        system_prompt=system_prompt,
        response_schema=PlannerOutput,
        max_retries=3,
        task_id=task_id,
        step_index=state["current_step"],
        agent_name="planner",
    )

    state["token_usage"] = state.get("token_usage", 0) + response.usage.total_tokens
    state["estimated_cost_usd"] = round(
        state.get("estimated_cost_usd", 0.0) + response.usage.cost_usd, 6
    )

    plan_data = response.structured or {
        "plan_summary": "Default plan",
        "subtasks": [
            {
                "order_index": 0,
                "title": "Information Research",
                "description": "Gather relevant technical facts and documentation.",
                "assigned_agent": "researcher",
                "dependencies": [],
            },
            {
                "order_index": 1,
                "title": "Operation Execution",
                "description": "Perform necessary computations and verification.",
                "assigned_agent": "executor",
                "dependencies": [0],
            },
        ],
    }

    subtasks = plan_data.get("subtasks", [])
    for st in subtasks:
        if "dependencies" not in st:
            st["dependencies"] = []

    state["subtasks"] = subtasks
    state["current_subtask_index"] = 0
    state["completed_subtask_indices"] = []
    state["rework_count"] = 0
    state["last_agent"] = "planner"

    messages = list(state.get("messages", []))
    messages.append({
        "role": "planner",
        "content": response.content,
        "plan_summary": plan_data.get("plan_summary"),
        "subtask_count": len(subtasks),
    })
    state["messages"] = messages

    if task_id and task_id != "unknown":
        record_execution_event(
            task_id=task_id,
            event_type="PLANNER_COMPLETED",
            message=f"Planner decomposed goal into {len(subtasks)} discrete subtasks",
            agent_name="planner",
            step_index=state["current_step"],
            details={"subtask_count": len(subtasks), "plan_summary": plan_data.get("plan_summary")},
        )

    return state
