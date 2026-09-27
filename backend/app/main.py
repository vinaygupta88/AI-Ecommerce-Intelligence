import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator

from backend.app.api.v1.router import api_router

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

app = FastAPI(
    title="AI E-Commerce Intelligence & Demand Forecasting Platform",
    description="Enterprise REST API for demand forecasting, stockout risk prediction, and inventory replenishment.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS middleware for Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Prometheus Metric Instrumentator Setup
instrumentator = Instrumentator(
    should_group_status_codes=True,
    should_ignore_untemplated=True,
    should_respect_env_var=False,
    excluded_handlers=["/metrics", "/docs", "/openapi.json"],
    env_var_name="ENABLE_METRICS",
)

# Mount Prometheus instrumentation before routes
instrumentator.instrument(app).expose(app, endpoint="/metrics", tags=["Monitoring"])

# Mount API Routers
app.include_router(api_router, prefix="/api/v1")


@app.on_event("startup")
def startup_event():
    logger.info("FastAPI backend engine started. Swagger: /docs | Prometheus: /metrics")


@app.on_event("shutdown")
def shutdown_event():
    logger.info("FastAPI backend engine shutting down.")


@app.get("/", tags=["Root"])
def root():
    return {
        "platform": "AI Supply Chain Intelligence",
        "documentation": "/docs",
        "metrics": "/metrics",
        "healthcheck": "/api/v1/health",
    }