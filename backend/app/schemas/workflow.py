from datetime import datetime
from typing import Optional, List, Dict, Any, Literal
from pydantic import BaseModel, Field, ConfigDict


NodeType = Literal[
    "start",
    "agent",
    "tool",
    "conditional",
    "approval",
    "parallel",
    "merge",
    "review",
    "end",
]


class WorkflowNode(BaseModel):
    id: str = Field(..., description="Unique node identifier within workflow")
    type: NodeType = Field(..., description="Workflow node archetype")
    label: str = Field(..., description="Human-readable node label")
    x: float = Field(default=100.0, description="Canvas X coordinate")
    y: float = Field(default=100.0, description="Canvas Y coordinate")
    config: Dict[str, Any] = Field(default_factory=dict, description="Node configuration attributes")


class WorkflowEdge(BaseModel):
    id: str = Field(..., description="Unique edge identifier")
    source: str = Field(..., description="Source node ID")
    target: str = Field(..., description="Target node ID")
    source_port: Optional[str] = Field(None, description="Conditional source port ('true' | 'false' | 'default')")
    target_port: Optional[str] = Field(None, description="Target input port")


class WorkflowDefinition(BaseModel):
    nodes: List[WorkflowNode] = Field(default_factory=list, description="Graph nodes")
    edges: List[WorkflowEdge] = Field(default_factory=list, description="Graph directed connections")
    variables: Dict[str, Any] = Field(default_factory=dict, description="Workflow initial runtime variables")


class WorkflowCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=128, description="Workflow name")
    description: Optional[str] = Field(None, max_length=1000, description="Workflow summary")
    definition: WorkflowDefinition = Field(..., description="Graph topology definition")
    is_enabled: bool = Field(default=True, description="Whether workflow is executable")


class WorkflowUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=128)
    description: Optional[str] = Field(None, max_length=1000)
    definition: Optional[WorkflowDefinition] = None
    is_enabled: Optional[bool] = None
    changelog: Optional[str] = Field(None, max_length=500, description="Version commit message")


class WorkflowResponse(BaseModel):
    id: str
    user_id: str
    workspace_id: str
    name: str
    description: Optional[str] = None
    version: int
    is_enabled: bool
    definition: WorkflowDefinition
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class WorkflowListResponse(BaseModel):
    total: int
    workflows: List[WorkflowResponse]


class WorkflowVersionResponse(BaseModel):
    id: str
    workflow_id: str
    version: int
    definition: WorkflowDefinition
    changelog: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ValidationErrorItem(BaseModel):
    node_id: Optional[str] = Field(None, description="Affected node ID")
    message: str = Field(..., description="Validation failure explanation")
    error_type: str = Field(..., description="Category: 'cycle', 'orphan', 'missing_start', 'schema', 'security'")


class WorkflowValidationResult(BaseModel):
    is_valid: bool
    errors: List[ValidationErrorItem] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)


class WorkflowRunCreate(BaseModel):
    initial_inputs: Dict[str, Any] = Field(default_factory=dict, description="Initial runtime variables")
    goal: Optional[str] = Field(None, description="Optional mission goal override")


class WorkflowRunResponse(BaseModel):
    id: str
    workflow_id: str
    version: int
    task_id: Optional[str] = None
    user_id: str
    workspace_id: str
    status: str
    node_states: Dict[str, Any]
    execution_context: Dict[str, Any]
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
