from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pymongo.errors import PyMongoError

from app.api.routes import router as api_router
from app.core.config import settings
from app.db.mongo import close_mongo_connection, connect_to_mongo


@asynccontextmanager
async def lifespan(_: FastAPI):
    connect_to_mongo()
    yield
    close_mongo_connection()


app = FastAPI(
    title=settings.app_name,
    description="A metadata-rich archive for discovering media across formats.",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.enable_docs else None,
    redoc_url="/redoc" if settings.enable_docs else None,
    openapi_url="/openapi.json" if settings.enable_docs else None,
)

templates = Jinja2Templates(directory=str(settings.templates_dir))

app.add_middleware(GZipMiddleware, minimum_size=500)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials="*" not in settings.cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory=str(settings.static_dir)), name="static")
app.include_router(api_router)


@app.exception_handler(PyMongoError)
async def mongo_exception_handler(_: Request, exc: PyMongoError) -> JSONResponse:
    return JSONResponse(
        status_code=500,
        content={"detail": f"Database operation failed: {exc}"},
    )


@app.get("/", response_class=HTMLResponse)
def homepage(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "app_name": settings.app_name,
        },
    )


@app.get("/items/{media_id}", response_class=HTMLResponse)
def detail_page(request: Request, media_id: str) -> HTMLResponse:
    return templates.TemplateResponse(
        "detail.html",
        {
            "request": request,
            "app_name": settings.app_name,
            "media_id": media_id,
        },
    )
