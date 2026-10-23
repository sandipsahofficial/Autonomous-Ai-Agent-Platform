from fastapi import APIRouter
from app.api.tasks import router as tasks_router
from app.api.tools import router as tools_router
from app.api.approvals import router as approvals_router, tasks_approvals_router
from app.api.audit import router as audit_router
from app.api.metrics import router as metrics_router
from app.api.memories import router as memories_router
from app.api.agents import router as agents_router
from app.api.workflows import router as workflows_router
from app.api.streaming import router as streaming_router
from app.api.schedules import router as schedules_router
from app.api.documents import router as documents_router
from app.api.templates import router as templates_router
from app.api.notifications import router as notifications_router
from app.api.model_router import router as model_router
from app.api.evaluations import router as evaluations_router
from app.api.auth import router as auth_router

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth_router)
api_router.include_router(tasks_router)
api_router.include_router(tools_router)
api_router.include_router(approvals_router)
api_router.include_router(tasks_approvals_router)
api_router.include_router(audit_router)
api_router.include_router(metrics_router)
api_router.include_router(memories_router)
api_router.include_router(agents_router)
api_router.include_router(workflows_router)
api_router.include_router(streaming_router)
api_router.include_router(schedules_router)
api_router.include_router(documents_router)
api_router.include_router(templates_router)
api_router.include_router(notifications_router)
api_router.include_router(model_router)
api_router.include_router(evaluations_router)
