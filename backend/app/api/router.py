from fastapi import APIRouter
from app.api.tasks import router as tasks_router
from app.api.tools import router as tools_router
from app.api.approvals import router as approvals_router, tasks_approvals_router
from app.api.audit import router as audit_router
from app.api.metrics import router as metrics_router

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(tasks_router)
api_router.include_router(tools_router)
api_router.include_router(approvals_router)
api_router.include_router(tasks_approvals_router)
api_router.include_router(audit_router)
api_router.include_router(metrics_router)
