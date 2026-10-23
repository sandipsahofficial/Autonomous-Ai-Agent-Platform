from typing import Optional, List, Dict, Any, Literal
from pydantic import BaseModel, Field


class ModelRouteRequest(BaseModel):
    task_category: Literal["research", "coding", "analysis", "general"] = Field(default="general")
    preferred_provider: Optional[Literal["ollama", "openai", "claude", "mock"]] = None
    has_private_documents: bool = Field(default=False, description="True if prompt contains sensitive user documents")
    token_budget: Optional[int] = Field(None, ge=100)
    cost_budget_usd: Optional[float] = Field(None, ge=0.0)


class ModelRouteDecision(BaseModel):
    selected_provider: str
    selected_model: str
    reason: str
    is_local_zero_cost: bool
    fallback_applied: bool = False
    candidate_providers: List[str] = Field(default_factory=list)


class ProviderStatusItem(BaseModel):
    provider_name: str
    is_available: bool
    is_configured: bool
    is_local: bool
    supported_models: List[str]
    latency_ms: Optional[float] = None
    last_error: Optional[str] = None


class ModelRouterStatusResponse(BaseModel):
    default_provider: str
    providers: List[ProviderStatusItem]
    active_routing_policy: str
