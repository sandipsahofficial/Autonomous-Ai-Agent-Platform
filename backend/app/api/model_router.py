from fastapi import APIRouter
from app.schemas.model_router import (
    ModelRouteRequest,
    ModelRouteDecision,
    ModelRouterStatusResponse,
)
from app.llm.router import ModelRouter

router = APIRouter(prefix="/models", tags=["Model Routing Engine"])


@router.get("/status", response_model=ModelRouterStatusResponse)
def get_model_routing_status():
    """
    Returns live health, latency, and capability configuration across all LLM providers.
    """
    return ModelRouter.get_provider_status()


@router.post("/route", response_model=ModelRouteDecision)
def compute_model_route(request: ModelRouteRequest):
    """
    Evaluates privacy constraints, user preference, and budgets to select the optimal model.
    Enforces privacy by routing missions with private documents strictly to local Ollama.
    """
    return ModelRouter.route(request)
