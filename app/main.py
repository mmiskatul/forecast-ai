import warnings

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from langchain_core._api.deprecation import LangChainPendingDeprecationWarning

warnings.filterwarnings(
    "ignore",
    message="The default value of `allowed_objects` will change in a future version.*",
    category=LangChainPendingDeprecationWarning,
)

from app.api.routes import router
from app.core.exceptions import register_exception_handlers

app = FastAPI(
    title="Forecast AI",
    description="Memory-aware forecasting API for Restock Radar.",
    version="1.0.0",
)
register_exception_handlers(app)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(router)
