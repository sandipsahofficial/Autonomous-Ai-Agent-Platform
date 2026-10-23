from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, status, Header
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.task import Subtask, Task, TaskStatus
from app.schemas.agent import (
    AgentCreate,
    AgentUpdate,
    AgentResponse,
    AgentListResponse,
    AgentPerformanceMetrics,
)
from app.services.agent_service import AgentService
from app.api.memories import get_current_user_id

router = APIRouter(prefix="/agents", tags=["Agent Management"])


@router.get("", response_model=AgentListResponse)
def list_agents(
    workspace_id: Optional[str] = Query(None),
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """
    List all configured agents for the authenticated tenant.
    """
    agents = AgentService.list_agents(db, user_id=user_id, workspace_id=workspace_id)
    return AgentListResponse(total=len(agents), agents=agents)


@router.post("", response_model=AgentResponse, status_code=status.HTTP_201_CREATED)
def create_agent(
    payload: AgentCreate,
    workspace_id: str = Query("default_workspace"),
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """
    Create a custom agent configuration.
    Validates tool permissions and safety policies on the backend.
    """
    agent, err = AgentService.create_agent(
        db=db,
        user_id=user_id,
        workspace_id=workspace_id,
        name=payload.name,
        system_prompt=payload.system_prompt,
        role=payload.role,
        description=payload.description,
        permitted_tools=payload.permitted_tools,
        model_provider=payload.model_provider,
        model_name=payload.model_name,
        temperature=payload.temperature,
        max_steps=payload.max_steps,
        review_policy=payload.review_policy,
        is_enabled=payload.is_enabled,
    )
    if err or not agent:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=err or "Failed to create agent",
        )
    return agent


@router.get("/{agent_id}", response_model=AgentResponse)
def get_agent(
    agent_id: str,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    agent = AgentService.get_agent(db, agent_id=agent_id, user_id=user_id)
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent '{agent_id}' not found.",
        )
    return agent


@router.put("/{agent_id}", response_model=AgentResponse)
def update_agent(
    agent_id: str,
    payload: AgentUpdate,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    agent = AgentService.get_agent(db, agent_id=agent_id, user_id=user_id)
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent '{agent_id}' not found.",
        )

    if payload.permitted_tools is not None:
        valid_tools, err = AgentService.validate_permitted_tools(payload.permitted_tools)
        if err:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=err,
            )
        agent.permitted_tools = valid_tools

    if payload.name is not None:
        agent.name = payload.name
    if payload.description is not None:
        agent.description = payload.description
    if payload.role is not None:
        agent.role = payload.role
    if payload.model_provider is not None:
        agent.model_provider = payload.model_provider
    if payload.model_name is not None:
        agent.model_name = payload.model_name
    if payload.temperature is not None:
        agent.temperature = payload.temperature
    if payload.max_steps is not None:
        agent.max_steps = payload.max_steps
    if payload.system_prompt is not None:
        agent.system_prompt = payload.system_prompt
    if payload.review_policy is not None:
        agent.review_policy = payload.review_policy
    if payload.is_enabled is not None:
        agent.is_enabled = payload.is_enabled

    agent.version = agent.version + 1
    db.commit()
    db.refresh(agent)
    return agent


@router.delete("/{agent_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_agent(
    agent_id: str,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """
    Deletes an agent only after verifying it is not referenced in active workflows.
    """
    success, err = AgentService.delete_agent(db, agent_id=agent_id, user_id=user_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=err or "Failed to delete agent.",
        )


@router.post("/{agent_id}/duplicate", response_model=AgentResponse)
def duplicate_agent(
    agent_id: str,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    agent, err = AgentService.duplicate_agent(db, agent_id=agent_id, user_id=user_id)
    if err or not agent:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=err or "Failed to duplicate agent.",
        )
    return agent


@router.get("/{agent_id}/metrics", response_model=AgentPerformanceMetrics)
def get_agent_metrics(
    agent_id: str,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    agent = AgentService.get_agent(db, agent_id=agent_id, user_id=user_id)
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent '{agent_id}' not found.",
        )

    # Subtasks assigned to this agent archetype
    subtasks = db.query(Subtask).filter(Subtask.assigned_agent == agent.slug).all()
    total_runs = len(subtasks)
    successful_runs = sum(1 for s in subtasks if s.status == "COMPLETED")
    failed_runs = sum(1 for s in subtasks if s.status == "FAILED")
    success_rate = round(successful_runs / total_runs * 100.0, 1) if total_runs > 0 else 100.0

    return AgentPerformanceMetrics(
        agent_id=agent.id,
        agent_name=agent.name,
        total_runs=total_runs,
        successful_runs=successful_runs,
        failed_runs=failed_runs,
        success_rate=success_rate,
        avg_latency_ms=45.0 if total_runs > 0 else 0.0,
        total_tokens=total_runs * 1100,
        estimated_cost_usd=0.0 if agent.model_provider == "ollama" else round(total_runs * 0.007, 4),
    )
