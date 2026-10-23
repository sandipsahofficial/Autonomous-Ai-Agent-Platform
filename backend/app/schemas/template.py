from datetime import datetime
from typing import Optional, List, Dict, Any, Literal
from pydantic import BaseModel, Field, ConfigDict


class TemplateCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=128)
    slug: str = Field(..., min_length=2, max_length=128)
    description: str = Field(..., min_length=5)
    template_type: Literal["agent", "workflow"] = Field(default="workflow")
    category: str = Field(default="general")
    version: str = Field(default="1.0.0")
    content: Dict[str, Any] = Field(..., description="Template parameters or node/edge topology")
    tags: List[str] = Field(default_factory=list)


class TemplateImportPayload(BaseModel):
    template_json: str = Field(..., description="Raw JSON string of exported template")


class TemplateResponse(BaseModel):
    id: str
    name: str
    slug: str
    description: str
    template_type: str
    category: str
    version: str
    content: Dict[str, Any]
    is_builtin: bool
    author: str
    tags: List[str]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TemplateListResponse(BaseModel):
    total: int
    templates: List[TemplateResponse]


class TemplateCloneResponse(BaseModel):
    success: bool
    message: str
    cloned_id: str
    cloned_type: str
