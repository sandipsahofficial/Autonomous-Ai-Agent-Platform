import time
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from app.models.workflow import Workflow, WorkflowRun
from app.models.task import Task, TaskStatus
from app.schemas.workflow import WorkflowDefinition, WorkflowNode
from app.services.trace_service import record_execution_event
from app.tools.registry import default_tool_registry
from app.safety.risk_scorer import assess_tool_risk


class WorkflowCompiler:
    """
    Translates visual workflow definitions into executable missions.
    Reuses existing LangGraph orchestration and execution events rather
    than spinning up a competing engine.
    """

    @classmethod
    def create_run(
        cls,
        db: Session,
        workflow: Workflow,
        user_id: str,
        workspace_id: str,
        initial_inputs: Dict[str, Any],
        goal_override: Optional[str] = None,
    ) -> WorkflowRun:
        definition = WorkflowDefinition(**(workflow.definition or {}))
        
        # Build initial node states map
        node_states = {}
        for n in definition.nodes:
            node_states[n.id] = {
                "status": "pending",
                "label": n.label,
                "type": n.type,
                "output": None,
                "error": None,
                "duration_ms": 0.0,
            }

        # Determine overall mission goal
        goal = goal_override or workflow.description or f"Execute Workflow: {workflow.name}"

        # Create underlying Task for unified execution telemetry and audit tracking
        task = Task(
            user_id=user_id,
            workspace_id=workspace_id,
            goal=goal,
            status=TaskStatus.RUNNING,
            current_stage="planner",
        )
        db.add(task)
        db.commit()
        db.refresh(task)

        # Create WorkflowRun
        wf_run = WorkflowRun(
            workflow_id=workflow.id,
            version=workflow.version,
            task_id=task.id,
            user_id=user_id,
            workspace_id=workspace_id,
            status="RUNNING",
            node_states=node_states,
            execution_context=initial_inputs or {},
        )
        db.add(wf_run)
        db.commit()
        db.refresh(wf_run)

        record_execution_event(
            task_id=task.id,
            event_type="WORKFLOW_STARTED",
            message=f"Workflow '{workflow.name}' (v{workflow.version}) dispatched",
            agent_name="orchestrator",
            step_index=0,
            status="SUCCESS",
            details={
                "workflow_id": workflow.id,
                "run_id": wf_run.id,
                "total_nodes": len(definition.nodes),
            },
        )

        return wf_run

    @classmethod
    def execute_sync_step(
        cls,
        db: Session,
        run_id: str,
        node_id: str,
    ) -> WorkflowRun:
        """
        Advances an individual node in the workflow run, recording its status,
        output, and duration.
        """
        run = db.query(WorkflowRun).filter(WorkflowRun.id == run_id).first()
        if not run:
            raise ValueError(f"WorkflowRun {run_id} not found")

        workflow = run.workflow
        definition = WorkflowDefinition(**(workflow.definition or {}))
        node_map = {n.id: n for n in definition.nodes}
        node = node_map.get(node_id)
        if not node:
            raise ValueError(f"Node {node_id} not found in workflow")

        node_states = dict(run.node_states or {})
        start_t = time.time()
        node_states[node_id]["status"] = "active"
        run.node_states = node_states
        db.commit()

        try:
            # Execute node based on type
            output = None
            if node.type == "start":
                output = {"status": "initialized", "inputs": run.execution_context}
            elif node.type == "end":
                output = {"status": "finalized", "result": "Workflow execution completed successfully"}
                run.status = "COMPLETED"
            elif node.type == "tool":
                tool_name = node.config.get("tool_name")
                args = node.config.get("arguments", {})
                res, risk = default_tool_registry.execute_with_safety_gate(
                    tool_name=tool_name,
                    arguments=args,
                    caller_permissions=["math:compute", "files:read", "docs:inspect"],
                )
                if not res.success:
                    raise RuntimeError(res.error or "Tool execution failed")
                output = res.output
            elif node.type == "approval":
                run.status = "WAITING_APPROVAL"
                output = {"status": "paused_for_approval", "reason": node.config.get("reason", "Operator authorization required")}
            else:
                output = {"status": "processed", "node_type": node.type}

            duration_ms = round((time.time() - start_t) * 1000, 2)
            node_states[node_id]["status"] = "waiting" if node.type == "approval" else "completed"
            node_states[node_id]["output"] = output
            node_states[node_id]["duration_ms"] = duration_ms

        except Exception as exc:
            duration_ms = round((time.time() - start_t) * 1000, 2)
            node_states[node_id]["status"] = "failed"
            node_states[node_id]["error"] = str(exc)
            node_states[node_id]["duration_ms"] = duration_ms
            run.status = "FAILED"
            run.error_message = f"Node '{node.label}' failed: {str(exc)}"

        run.node_states = node_states
        db.commit()
        db.refresh(run)

        if run.task_id:
            record_execution_event(
                task_id=run.task_id,
                event_type="NODE_COMPLETED" if node_states[node_id]["status"] == "completed" else "NODE_FAILED",
                message=f"Node '{node.label}' ({node.type}) finished with status {node_states[node_id]['status']}",
                agent_name="workflow_engine",
                step_index=1,
                status="SUCCESS" if node_states[node_id]["status"] == "completed" else "FAILED",
                duration_ms=duration_ms,
                details={"node_id": node_id, "node_type": node.type},
            )

        return run
