from datetime import datetime
from typing import Optional, List, Dict, Any, Literal
from pydantic import BaseModel, Field, ConfigDict


class AgentCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=128, description="Display name of the agent")
    description: Optional[str] = Field(None, max_length=1000, description="Functional summary of responsibilities")
    role: str = Field(default="custom", max_length=64, description="Agent specialization or archetype")
    permitted_tools: List[str] = Field(default_factory=list, description="Explicit whitelist of permitted tool names")
    model_provider: Literal["ollama", "openai", "claude", "mock"] = Field(
        default="ollama", description="Configured LLM inference engine"
    )
    model_name: str = Field(default="llama3", max_length=64, description="Model checkpoint name")
    temperature: float = Field(default=0.7, ge=0.0, le=2.0, description="Sampling randomness")
    max_steps: int = Field(default=10, ge=1, le=50, description="Step budget limit for this agent")
    system_prompt: str = Field(..., min_length=10, description="Approved system behavior instructions")
    review_policy: Literal["strict", "standard", "lenient", "none"] = Field(
        default="standard", description="Validation and review threshold"
    )
    is_enabled: bool = Field(default=True, description="Whether agent is active for dispatch")


class AgentUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=128)
    description: Optional[str] = Field(None, max_length=1000)
    role: Optional[str] = Field(None, max_length=64)
    permitted_tools: Optional[List[str]] = None
    model_provider: Optional[Literal["ollama", "openai", "claude", "mock"]] = None
    model_name: Optional[str] = None
    temperature: Optional[float] = Field(None, ge=0.0, le=2.0)
    max_steps: Optional[int] = Field(None, ge=1, le=50)
    system_prompt: Optional[str] = Field(None, min_length=10)
    review_policy: Optional[Literal["strict", "standard", "lenient", "none"]] = None
    is_enabled: Optional[bool] = None


class AgentResponse(BaseModel):
    id: str
    user_id: str
    workspace_id: str
    name: str
    slug: str
    description: Optional[str] = None
    role: str
    permitted_tools: List[str]
    model_provider: str
    model_name: str
    temperature: float
    max_steps: int
    system_prompt: str
    review_policy: str
    is_enabled: bool
    is_system: bool
    version: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AgentListResponse(BaseModel):
    total: int
    agents: List[AgentResponse]


class AgentPerformanceMetrics(BaseModel):
    agent_id: str
    agent_name: str
    total_runs: int
    successful_runs: int
    failed_runs: int
    success_rate: float
    avg_latency_ms: float
    total_tokens: int
    estimated_cost_usd: float
