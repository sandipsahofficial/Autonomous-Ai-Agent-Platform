from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import Response
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas.template import (
    TemplateResponse,
    TemplateListResponse,
    TemplateCloneResponse,
    TemplateImportPayload,
)
from app.services.template_service import TemplateService
from app.api.memories import get_current_user_id

router = APIRouter(prefix="/templates", tags=["Template Library"])


@router.get("", response_model=TemplateListResponse)
def list_templates(
    category: Optional[str] = Query(None),
    template_type: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    items = TemplateService.list_templates(db, category=category, template_type=template_type, search=search)
    return TemplateListResponse(total=len(items), templates=items)


@router.get("/{template_id}", response_model=TemplateResponse)
def get_template(
    template_id: str,
    db: Session = Depends(get_db),
):
    t = TemplateService.get_template(db, template_id)
    if not t:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Template '{template_id}' not found.",
        )
    return t


@router.post("/{template_id}/clone", response_model=TemplateCloneResponse)
def clone_template(
    template_id: str,
    custom_name: Optional[str] = Query(None),
    workspace_id: str = Query("default_workspace"),
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    success, msg, cloned_id, ctype = TemplateService.clone_template(
        db=db,
        template_id=template_id,
        user_id=user_id,
        workspace_id=workspace_id,
        custom_name=custom_name,
    )
    if not success or not cloned_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=msg,
        )
    return TemplateCloneResponse(
        success=True,
        message=msg,
        cloned_id=cloned_id,
        cloned_type=ctype or "workflow",
    )


@router.get("/{template_id}/export")
def export_template(
    template_id: str,
    db: Session = Depends(get_db),
):
    json_str, err = TemplateService.export_template_json(db, template_id)
    if err or not json_str:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=err or "Failed to export template.",
        )
    return Response(
        content=json_str,
        media_type="application/json",
        headers={"Content-Disposition": f"attachment; filename=template_{template_id[:8]}.json"},
    )


@router.post("/import", response_model=TemplateResponse, status_code=status.HTTP_201_CREATED)
def import_template(
    payload: TemplateImportPayload,
    db: Session = Depends(get_db),
):
    template, err = TemplateService.import_template_json(db, payload.template_json)
    if err or not template:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=err or "Failed to import template.",
        )
    return template
