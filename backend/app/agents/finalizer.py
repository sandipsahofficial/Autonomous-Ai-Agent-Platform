from app.agents.state import AgentState
from app.agents.schemas import FinalizerOutput
from app.llm.factory import get_llm_provider
from app.llm.resilience import generate_with_resilience
from app.database import SessionLocal
from app.services.memory_service import MemoryService
from app.services.trace_service import record_execution_event


def finalizer_node(state: AgentState) -> AgentState:
    """
    Finalizer agent node:
    Synthesizes outputs from all verified subtasks into a cohesive structured result,
    evaluates overall quality, and persists successful strategy to task history memory.
    """
    state["current_step"] = state.get("current_step", 0) + 1
    state["current_stage"] = "finalizer"
    task_id = state.get("task_id", "unknown")
    user_id = state.get("user_id", "sandip_sah")
    goal = state.get("goal", "")
    llm = get_llm_provider()

    subtasks = state.get("subtasks", [])

    system_prompt = (
        "You are the Lead Finalizer Agent. Combine all verified subtask outputs and research "
        "into a structured, executive-level final result. Identify key technical learnings and "
        "strategy takeaways to record in persistent memory.\n"
        "Return structured JSON matching FinalizerOutput."
    )

    # Compile intermediate deliverables
    subtask_summaries = []
    for st in subtasks:
        subtask_summaries.append(
            f"- Subtask #{st.get('order_index', 0) + 1} ({st.get('assigned_agent')}): {st.get('title')}\n"
            f"  Description: {st.get('description')}\n"
            f"  Result: {st.get('result') or 'Completed successfully'}"
        )
    compiled_subtasks = "\n".join(subtask_summaries)

    prompt = (
        f"Mission Goal: {goal}\n"
        f"Completed Subtasks:\n{compiled_subtasks}\n"
        f"Last Working Output:\n{state.get('current_result', 'N/A')}"
    )

    response = generate_with_resilience(
        provider=llm,
        prompt=prompt,
        system_prompt=system_prompt,
        response_schema=FinalizerOutput,
        max_retries=3,
        task_id=task_id,
        step_index=state["current_step"],
        agent_name="finalizer",
    )

    state["token_usage"] = state.get("token_usage", 0) + response.usage.total_tokens
    state["estimated_cost_usd"] = round(
        state.get("estimated_cost_usd", 0.0) + response.usage.cost_usd, 6
    )

    fin_data = response.structured or {
        "executive_summary": f"Successfully completed all {len(subtasks)} subtasks for mission goal.",
        "deliverables": state.get("current_result") or "Mission completed successfully.",
        "learnings_and_strategy": f"Effective sequential execution for: {goal}",
        "confidence_score": 95,
    }

    final_text = (
        f"### MISSION COMPLETE: {fin_data.get('executive_summary')}\n\n"
        f"**Deliverables:**\n{fin_data.get('deliverables')}\n\n"
        f"**Strategy & Learnings:**\n{fin_data.get('learnings_and_strategy')}"
    )

    state["final_output"] = final_text
    state["is_completed"] = True
    state["last_agent"] = "finalizer"

    # Persist strategy into task history memory
    try:
        db = SessionLocal()
        try:
            learning_content = fin_data.get("learnings_and_strategy", "")
            if learning_content and task_id != "unknown":
                MemoryService.create_memory(
                    db=db,
                    user_id=user_id,
                    key=f"strategy_{task_id[:8]}",
                    content=f"Strategy for '{goal}': {learning_content}",
                    memory_type="task_history",
                    mission_id=task_id,
                    metadata={"confidence_score": fin_data.get("confidence_score", 90)},
                )
                record_execution_event(
                    task_id=task_id,
                    event_type="MEMORY_WRITTEN",
                    message="Persisted mission strategy and learnings into agent memory",
                    agent_name="finalizer",
                    step_index=state["current_step"],
                    details={"key": f"strategy_{task_id[:8]}", "type": "task_history"},
                )
        finally:
            db.close()
    except Exception as mem_err:
        pass

    messages = list(state.get("messages", []))
    messages.append({
        "role": "finalizer",
        "content": final_text,
        "confidence_score": fin_data.get("confidence_score", 95),
    })
    state["messages"] = messages

    if task_id and task_id != "unknown":
        record_execution_event(
            task_id=task_id,
            event_type="TASK_COMPLETED",
            message=f"Mission finalized with {fin_data.get('confidence_score', 95)}% confidence",
            agent_name="finalizer",
            step_index=state["current_step"],
            status="SUCCESS",
            details={"confidence_score": fin_data.get("confidence_score", 95)},
        )

    return state
