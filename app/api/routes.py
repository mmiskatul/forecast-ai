from __future__ import annotations

from fastapi import APIRouter

from app.core.exceptions import ForecastAPIError
from app.graphs.forecast_graph import run_forecast_graph
from app.schemas import ForecastInput, ForecastOutput

router = APIRouter()


@router.get("/")
def root() -> dict[str, str]:
    return {"message": "Forecast AI API is running"}


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "Forecast AI"}


@router.post("/forecast", response_model=ForecastOutput)
async def forecast(payload: ForecastInput) -> ForecastOutput:
    try:
        return await run_forecast_graph(payload)
    except ForecastAPIError:
        raise
    except Exception as exc:
        raise ForecastAPIError(
            "Forecast graph failed to produce a valid response.",
            code="forecast_graph_failed",
            status_code=500,
        ) from exc
