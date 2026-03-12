from fastapi import APIRouter

from app.api.routes.auth import router as auth_router
from app.api.routes.billing import router as billing_router
from app.api.routes.convert import router as convert_router
from app.api.routes.download import router as download_router
from app.api.routes.edit import router as edit_router
from app.api.routes.health import router as health_router
from app.api.routes.history import router as history_router
from app.api.routes.intelligence import router as intelligence_router
from app.api.routes.jobs import router as jobs_router
from app.api.routes.optimize import router as optimize_router
from app.api.routes.organize import router as organize_router
from app.api.routes.security import router as security_router
from app.api.routes.uploads import router as uploads_router
from app.api.routes.users import router as users_router

api_router = APIRouter()
api_router.include_router(auth_router, prefix="/auth", tags=["auth"])
api_router.include_router(billing_router, tags=["billing"])
api_router.include_router(convert_router, tags=["convert"])
api_router.include_router(download_router, tags=["download"])
api_router.include_router(edit_router, tags=["edit"])
api_router.include_router(health_router, prefix="/health", tags=["health"])
api_router.include_router(history_router, tags=["history"])
api_router.include_router(intelligence_router, tags=["intelligence"])
api_router.include_router(jobs_router, tags=["jobs"])
api_router.include_router(optimize_router, tags=["optimize"])
api_router.include_router(organize_router, tags=["organize"])
api_router.include_router(security_router, tags=["security"])
api_router.include_router(uploads_router, tags=["uploads"])
api_router.include_router(users_router, tags=["users"])
