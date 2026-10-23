from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy.orm import Session
from app.models.workflow import Workflow, WorkflowVersion, WorkflowRun
from app.schemas.workflow import WorkflowCreate, WorkflowUpdate, WorkflowDefinition, WorkflowValidationResult
from app.workflows.validator import WorkflowValidator
from app.workflows.compiler import WorkflowCompiler


class WorkflowService:
    @staticmethod
    def create_workflow(
        db: Session,
        user_id: str,
        workspace_id: str,
        payload: WorkflowCreate,
    ) -> Tuple[Optional[Workflow], Optional[WorkflowValidationResult]]:
        # Validate topology and security
        validation = WorkflowValidator.validate(payload.definition)
        if not validation.is_valid:
            return None, validation

        raw_def = payload.definition.model_dump()

        workflow = Workflow(
            user_id=user_id,
            workspace_id=workspace_id,
            name=payload.name,
            description=payload.description,
            version=1,
            is_enabled=payload.is_enabled,
            definition=raw_def,
        )
        db.add(workflow)
        db.commit()
        db.refresh(workflow)

        # Store initial version snapshot
        version_snapshot = WorkflowVersion(
            workflow_id=workflow.id,
            version=1,
            definition=raw_def,
            changelog="Initial workflow version creation",
        )
        db.add(version_snapshot)
        db.commit()

        return workflow, None

    @staticmethod
    def update_workflow(
        db: Session,
        workflow_id: str,
        user_id: str,
        payload: WorkflowUpdate,
    ) -> Tuple[Optional[Workflow], Optional[WorkflowValidationResult]]:
        workflow = db.query(Workflow).filter(
            Workflow.id == workflow_id,
            Workflow.user_id == user_id,
        ).first()
        if not workflow:
            return None, None

        if payload.name is not None:
            workflow.name = payload.name
        if payload.description is not None:
            workflow.description = payload.description
        if payload.is_enabled is not None:
            workflow.is_enabled = payload.is_enabled

        if payload.definition is not None:
            validation = WorkflowValidator.validate(payload.definition)
            if not validation.is_valid:
                return None, validation

            new_version = workflow.version + 1
            workflow.version = new_version
            raw_def = payload.definition.model_dump()
            workflow.definition = raw_def

            # Persist version snapshot
            version_snapshot = WorkflowVersion(
                workflow_id=workflow.id,
                version=new_version,
                definition=raw_def,
                changelog=payload.changelog or f"Updated to version {new_version}",
            )
            db.add(version_snapshot)

        db.commit()
        db.refresh(workflow)
        return workflow, None

    @staticmethod
    def list_workflows(db: Session, user_id: str, workspace_id: Optional[str] = None) -> List[Workflow]:
        q = db.query(Workflow).filter(Workflow.user_id == user_id)
        if workspace_id:
            q = q.filter(Workflow.workspace_id == workspace_id)
        return q.order_by(Workflow.updated_at.desc()).all()

    @staticmethod
    def get_workflow(db: Session, workflow_id: str, user_id: str) -> Optional[Workflow]:
        return db.query(Workflow).filter(
            Workflow.id == workflow_id,
            Workflow.user_id == user_id,
        ).first()

    @staticmethod
    def delete_workflow(db: Session, workflow_id: str, user_id: str) -> bool:
        workflow = WorkflowService.get_workflow(db, workflow_id, user_id)
        if not workflow:
            return False
        db.delete(workflow)
        db.commit()
        return True

    @staticmethod
    def duplicate_workflow(db: Session, workflow_id: str, user_id: str) -> Optional[Workflow]:
        original = WorkflowService.get_workflow(db, workflow_id, user_id)
        if not original:
            return None
        
        dup_payload = WorkflowCreate(
            name=f"{original.name} (Copy)",
            description=original.description,
            definition=WorkflowDefinition(**(original.definition or {})),
            is_enabled=original.is_enabled,
        )
        wf, _ = WorkflowService.create_workflow(db, user_id, original.workspace_id, dup_payload)
        return wf
