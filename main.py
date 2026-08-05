from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings

def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        openapi_url=f"{settings.API_V1_STR}/openapi.json",
        description="CareerShift Enterprise Backend API",
        version="1.0.0",
    )

    # Set all CORS enabled origins
    if settings.BACKEND_CORS_ORIGINS:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=[str(origin).rstrip("/") for origin in settings.BACKEND_CORS_ORIGINS],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    from app.middleware.timing import RequestTimingMiddleware
    
    app.add_middleware(RequestTimingMiddleware)

    from app.api.v1.auth.routes import router as auth_router
    from app.api.v1.users.routes import router as users_router
    from app.api.v1.profile.routes import router as profile_router
    from app.api.v1.master.routes import router as master_router
    from app.api.v1.assessment.routes import router as assessment_router
    from app.api.v1.assessment.task_routes import router as assessment_task_router
    from app.api.v1.assessment.analysis_routes import router as assessment_analysis_router
    from app.api.v1.assessment.readiness_routes import router as assessment_readiness_router
    from app.middleware.exception_handler import add_exception_handlers
    
    app.include_router(auth_router, prefix=f"{settings.API_V1_STR}/auth", tags=["Auth"])
    app.include_router(users_router, prefix=f"{settings.API_V1_STR}/users", tags=["Users"])
    app.include_router(profile_router, prefix=f"{settings.API_V1_STR}/profile", tags=["Profile"])
    app.include_router(master_router, prefix=f"{settings.API_V1_STR}/master", tags=["Master Data"])
    app.include_router(assessment_router, prefix=f"{settings.API_V1_STR}/assessment", tags=["Assessment"])
    app.include_router(
        assessment_task_router,
        prefix=f"{settings.API_V1_STR}/assessment",
        tags=["Assessment Tasks"],
    )
    app.include_router(
        assessment_analysis_router,
        prefix=f"{settings.API_V1_STR}/assessment",
        tags=["Assessment 3B Analysis"],
    )
    app.include_router(
        assessment_readiness_router,
        prefix=f"{settings.API_V1_STR}/assessment",
        tags=["Assessment AI Readiness"],
    )

    add_exception_handlers(app)

    @app.get("/health", tags=["Health"])
    async def health_check():
        return {"status": "ok", "environment": settings.ENVIRONMENT}

    return app

app = create_app()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
