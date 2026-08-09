import logging

from fastapi import Request, FastAPI
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

from app.core.config import settings
from app.exceptions.custom import BaseAPIException
from app.schemas.common import APIResponse

logger = logging.getLogger(__name__)


def add_exception_handlers(app: FastAPI):
    @app.exception_handler(BaseAPIException)
    async def custom_api_exception_handler(request: Request, exc: BaseAPIException):
        response = APIResponse(
            success=False,
            message=exc.message,
            errors=[exc.message]
        )
        return JSONResponse(status_code=exc.status_code, content=response.model_dump(mode="json"))

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        response = APIResponse(
            success=False,
            message="Validation error",
            errors=[str(err) for err in exc.errors()]
        )
        return JSONResponse(status_code=422, content=response.model_dump(mode="json"))
        
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        request_id = getattr(request.state, "request_id", None)
        logger.exception(
            "Unhandled exception request_id=%s path=%s",
            request_id,
            request.url.path,
        )
        errors = [str(exc)] if not settings.is_production else ["An unexpected error occurred."]
        response = APIResponse(
            success=False,
            message="Internal server error",
            errors=errors,
        )
        return JSONResponse(status_code=500, content=response.model_dump(mode="json"))
