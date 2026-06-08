from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


ForecastType = Literal["daily", "weekly", "monthly"]
ForecastTrend = Literal["increasing", "stable", "declining"]
ForecastLevel = Literal["high", "medium", "low"]


class ForecastInput(BaseModel):
    model_config = ConfigDict(extra="allow")

    current_data: dict[str, Any] = Field(default_factory=dict)
    memory: dict[str, Any] = Field(default_factory=dict)


class ChannelInsights(BaseModel):
    top_channel: str
    fastest_growing_channel: str
    underperforming_channel: str


class ForecastingResult(BaseModel):
    trend: ForecastTrend
    demand_level: ForecastLevel
    risk_level: ForecastLevel
    confidence_score: float = Field(ge=0, le=1)
    stockout_prediction_days: int = Field(ge=0)
    forecast_summary: str
    learning_notes: str
    channel_insights: ChannelInsights
    recommendations: list[str]


class MemoryResult(BaseModel):
    forecast_snapshot: dict[str, Any]
    learning_signal: dict[str, Any]
    backend_storage_notes: str


class ForecastOutput(BaseModel):
    forecasting: ForecastingResult
    memory: MemoryResult
