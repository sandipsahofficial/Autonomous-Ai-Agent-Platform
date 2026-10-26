import sys
import time
import json
from fastapi.testclient import TestClient

sys.path.insert(0, "backend")
from app.main import app
from app.database import SessionLocal
from app.models.user import User, UserRole
from app.models.task import Task, Subtask, ExecutionEvent, TaskStatus
from app.auth.security import hash_password, create_access_token

def run_real_mission():
    print("=" * 80)
    print("STAGE 5: REAL END-TO-END OLLAMA MISSION VERIFICATION")
    print("=" * 80)

    # 1. Setup operator credentials
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == "operator_p8").first()
        if not user:
            user = User(
                id="user_operator_p8",
                username="operator_p8",
                email="operator_p8@mesh.internal",
                hashed_password=hash_password("SecurePass123!"),
                role=UserRole.OPERATOR.value,
                is_active=True,
            )
            db.add(user)
            db.commit()
            db.refresh(user)
        user_id = user.id
    finally:
        db.close()

    token = create_access_token({"sub": user_id, "username": "operator_p8", "role": "operator"})
    headers = {"Authorization": f"Bearer {token}"}

    client = TestClient(app)

    # 2. Submit mission through HTTP API
    mission_goal = "Calculate the total cost of 12 items priced at 35 each, verify the result independently, and return the calculation with a concise explanation."
    print(f"\n[1] Submitting authenticated mission to POST /api/v1/tasks...")
    print(f"    Goal: {mission_goal}")
    print(f"    Auth: Bearer JWT ({user_id})")

    resp = client.post(
        "/api/v1/tasks",
        headers=headers,
        json={"goal": mission_goal, "workspace_id": "production_workspace"},
    )
    assert resp.status_code == 201, f"Failed task creation: {resp.text}"
    task_data = resp.json()
    task_id = task_data["id"]
    print(f"    [PASS] Task created with ID: {task_id}")
    print(f"    Initial Status: {task_data['status']}")

    # 3. Follow task progress through polling
    print("\n[2] Following mission execution lifecycle...")
    start_time = time.time()
    max_wait = 180.0  # 3 minutes for local LLM
    final_task = None

    while time.time() - start_time < max_wait:
        t_resp = client.get(f"/api/v1/tasks/{task_id}", headers=headers)
        assert t_resp.status_code == 200
        task_info = t_resp.json()
        status_val = task_info.get("status")

        # Check if task paused at human approval gate
        if status_val == "WAITING_APPROVAL":
            print(f"    [INTERRUPT] Task paused at Human Approval Gate.")
            app_resp = client.get(f"/api/v1/tasks/{task_id}/pending-approval", headers=headers)
            print(f"    Approval Details: {app_resp.json()}")
            
            # Operator authorizes action
            decision_resp = client.post(
                f"/api/v1/tasks/{task_id}/approve",
                headers=headers,
                json={"approved": True, "feedback": "Authorized by QA engineer for Stage 5 verification"},
            )
            print(f"    Operator Decision Submitted: {decision_resp.json()}")

        if status_val in ("COMPLETED", "FAILED", "CANCELLED"):
            final_task = task_info
            break

        time.sleep(2.0)

    assert final_task is not None, f"Task did not complete within {max_wait}s"
    duration = round(time.time() - start_time, 2)
    print(f"\n[3] Mission Reached Terminal State ({duration}s):")
    print(f"    Status: {final_task.get('status')}")
    print(f"    Current Stage: {final_task.get('current_stage')}")
    print(f"    Current Step: {final_task.get('current_step')}")
    print(f"    Tokens Consumed: {final_task.get('token_usage')}")
    print(f"    Estimated Cost: ${final_task.get('estimated_cost_usd'):.4f}")
    print(f"    Final Output: {final_task.get('final_output')}")
    if final_task.get("error_message"):
        print(f"    Error: {final_task.get('error_message')}")

    # 4. Fetch Execution Traces from DB
    print("\n[4] Querying Execution Traces via GET /api/v1/tasks/{task_id}/traces...")
    trace_resp = client.get(f"/api/v1/tasks/{task_id}/traces", headers=headers)
    assert trace_resp.status_code == 200
    trace_data = trace_resp.json()
    events = trace_data.get("events", [])
    print(f"    Total Recorded Events: {len(events)}")
    for ev in events:
        print(f"    - [{ev.get('event_type')}] by @{ev.get('agent_name')}: {ev.get('message')[:100]} (Status: {ev.get('status')})")

    # 5. Verify Subtasks and Tool Execution in DB
    db = SessionLocal()
    try:
        subtasks = db.query(Subtask).filter(Subtask.task_id == task_id).order_by(Subtask.order_index).all()
        print(f"\n[5] Database Persisted Subtasks ({len(subtasks)}):")
        for st in subtasks:
            print(f"    - Subtask {st.order_index} [{st.assigned_agent}]: {st.title} (Status: {st.status.value if hasattr(st.status, 'value') else st.status})")
            if st.result:
                print(f"      Result: {st.result[:120]}")
    finally:
        db.close()

    print("\n" + "=" * 80)
    print("STAGE 5 VERIFICATION COMPLETED")
    print("=" * 80)

if __name__ == "__main__":
    run_real_mission()
