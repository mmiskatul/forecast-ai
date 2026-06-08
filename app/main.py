import warnings

from fastapi import FastAPI
from langchain_core._api.deprecation import LangChainPendingDeprecationWarning

warnings.filterwarnings(
    "ignore",
    message="The default value of `allowed_objects` will change in a future version.*",
    category=LangChainPendingDeprecationWarning,
)

from app.schemas import ForecastInput, ForecastOutput
from app.services.forecast_graph import run_forecast_graph

app = FastAPI(
    title="Forecast AI",
    description="Memory-aware forecasting API for Restock Radar.",
    version="1.0.0",
)


@app.get("/")
def root() -> dict[str, str]:
    return {"message": "Forecast AI API is running"}


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "Forecast AI"}


@app.post("/forecast", response_model=ForecastOutput)
async def forecast(payload: ForecastInput) -> ForecastOutput:
    return await run_forecast_graph(payload)
