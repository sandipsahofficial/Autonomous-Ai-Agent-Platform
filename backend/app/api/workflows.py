from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.workflow import Workflow, WorkflowVersion, WorkflowRun
from app.schemas.workflow import (
    WorkflowCreate,
    WorkflowUpdate,
    WorkflowResponse,
    WorkflowListResponse,
    WorkflowVersionResponse,
    WorkflowValidationResult,
    WorkflowDefinition,
    WorkflowRunCreate,
    WorkflowRunResponse,
)
from app.services.workflow_service import WorkflowService
from app.workflows.validator import WorkflowValidator
from app.workflows.compiler import WorkflowCompiler
from app.auth.dependencies import get_current_user
from app.models.user import User, UserRole

router = APIRouter(prefix="/workflows", tags=["Visual Workflow Automation"])


@router.post("/validate", response_model=WorkflowValidationResult)
def validate_workflow(definition: WorkflowDefinition):
    """
    Validates a proposed workflow topology.
    Detects cycles, orphaned nodes, schema mismatches, and security policies.
    """
    return WorkflowValidator.validate(definition)


@router.get("", response_model=WorkflowListResponse)
def list_workflows(
    workspace_id: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    workflows = WorkflowService.list_workflows(db, user_id=current_user.id, workspace_id=workspace_id)
    return WorkflowListResponse(total=len(workflows), workflows=workflows)


@router.post("", response_model=WorkflowResponse, status_code=status.HTTP_201_CREATED)
def create_workflow(
    payload: WorkflowCreate,
    workspace_id: str = Query("default_workspace"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.role not in (UserRole.ADMIN.value, UserRole.OPERATOR.value):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Forbidden: role '{current_user.role}' cannot create workflows.",
        )
    wf, val_err = WorkflowService.create_workflow(db, current_user.id, workspace_id, payload)
    if val_err:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "message": "Workflow topology validation failed.",
                "errors": [e.model_dump() for e in val_err.errors],
                "warnings": val_err.warnings,
            },
        )
    return wf


@router.get("/{workflow_id}", response_model=WorkflowResponse)
def get_workflow(
    workflow_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    wf = WorkflowService.get_workflow(db, workflow_id, current_user.id)
    if not wf:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow '{workflow_id}' not found.",
        )
    return wf


@router.put("/{workflow_id}", response_model=WorkflowResponse)
def update_workflow(
    workflow_id: str,
    payload: WorkflowUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.role not in (UserRole.ADMIN.value, UserRole.OPERATOR.value):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Forbidden: role '{current_user.role}' cannot update workflows.",
        )
    wf, val_err = WorkflowService.update_workflow(db, workflow_id, current_user.id, payload)
    if val_err:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "message": "Workflow topology validation failed.",
                "errors": [e.model_dump() for e in val_err.errors],
                "warnings": val_err.warnings,
            },
        )
    if not wf:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow '{workflow_id}' not found.",
        )
    return wf


@router.delete("/{workflow_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_workflow(
    workflow_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.role not in (UserRole.ADMIN.value, UserRole.OPERATOR.value):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Forbidden: role '{current_user.role}' cannot delete workflows.",
        )
    if not WorkflowService.delete_workflow(db, workflow_id, current_user.id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow '{workflow_id}' not found.",
        )


@router.post("/{workflow_id}/duplicate", response_model=WorkflowResponse)
def duplicate_workflow(
    workflow_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.role not in (UserRole.ADMIN.value, UserRole.OPERATOR.value):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Forbidden: role '{current_user.role}' cannot duplicate workflows.",
        )
    wf = WorkflowService.duplicate_workflow(db, workflow_id, current_user.id)
    if not wf:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow '{workflow_id}' not found.",
        )
    return wf


@router.get("/{workflow_id}/versions", response_model=List[WorkflowVersionResponse])
def list_workflow_versions(
    workflow_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    wf = WorkflowService.get_workflow(db, workflow_id, current_user.id)
    if not wf:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow '{workflow_id}' not found.",
        )
    return wf.versions


@router.post("/{workflow_id}/runs", response_model=WorkflowRunResponse, status_code=status.HTTP_201_CREATED)
def dispatch_workflow_run(
    workflow_id: str,
    payload: WorkflowRunCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.role not in (UserRole.ADMIN.value, UserRole.OPERATOR.value):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Forbidden: role '{current_user.role}' cannot execute workflows.",
        )
    wf = WorkflowService.get_workflow(db, workflow_id, current_user.id)
    if not wf:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow '{workflow_id}' not found.",
        )
    if not wf.is_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Workflow '{wf.name}' is currently disabled.",
        )

    run = WorkflowCompiler.create_run(
        db=db,
        workflow=wf,
        user_id=current_user.id,
        workspace_id=wf.workspace_id,
        initial_inputs=payload.initial_inputs,
        goal_override=payload.goal,
    )
    return run


@router.get("/{workflow_id}/runs", response_model=List[WorkflowRunResponse])
def list_workflow_runs(
    workflow_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    wf = WorkflowService.get_workflow(db, workflow_id, current_user.id)
    if not wf:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow '{workflow_id}' not found.",
        )
    return wf.runs


@router.get("/runs/{run_id}", response_model=WorkflowRunResponse)
def get_workflow_run(
    run_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    run = db.query(WorkflowRun).filter(WorkflowRun.id == run_id).first()
    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"WorkflowRun '{run_id}' not found.",
        )
    if current_user.role != UserRole.ADMIN.value and run.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Forbidden: access denied to workflow run '{run_id}'.",
        )
    return run


@router.post("/runs/{run_id}/step", response_model=WorkflowRunResponse)
def step_workflow_run(
    run_id: str,
    node_id: str = Query(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Advances a specific node within a live workflow run and records telemetry.
    """
    if current_user.role not in (UserRole.ADMIN.value, UserRole.OPERATOR.value):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Forbidden: role '{current_user.role}' cannot step workflow runs.",
        )
    run = db.query(WorkflowRun).filter(WorkflowRun.id == run_id).first()
    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"WorkflowRun '{run_id}' not found.",
        )
    if current_user.role != UserRole.ADMIN.value and run.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Forbidden: access denied to workflow run '{run_id}'.",
        )
    try:
        updated_run = WorkflowCompiler.execute_sync_step(db, run_id, node_id)
        return updated_run
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )
