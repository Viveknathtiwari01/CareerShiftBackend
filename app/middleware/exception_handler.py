from fastapi import Request, FastAPI
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from app.exceptions.custom import BaseAPIException
from app.schemas.common import APIResponse
from app.core.config import settings
import logging

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
        logger.exception("Unhandled exception on %s", request.url.path)
        if settings.is_production:
            response = APIResponse(
                success=False,
                message="Internal server error",
                errors=["An unexpected error occurred. Please try again later."],
            )
        else:
            response = APIResponse(
                success=False,
                message="Internal server error",
                errors=[str(exc)],
            )
        return JSONResponse(status_code=500, content=response.model_dump(mode="json"))
