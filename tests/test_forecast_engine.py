import json
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app


def test_forecast_endpoint_returns_strict_json_shape(monkeypatch):
    monkeypatch.setenv("OPENAI_ENABLED", "false")
    payload = json.loads(Path("examples/sample-input.json").read_text())
    client = TestClient(app)

    response = client.post("/forecast", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert set(data) == {"forecasting", "memory"}
    forecasting = data["forecasting"]
    assert forecasting["trend"] in {"increasing", "stable", "declining"}
    assert forecasting["demand_level"] in {"high", "medium", "low"}
    assert forecasting["risk_level"] in {"high", "medium", "low"}
    assert 0 <= forecasting["confidence_score"] <= 1
    assert isinstance(forecasting["stockout_prediction_days"], int)
    assert set(forecasting["channel_insights"]) == {
        "top_channel",
        "fastest_growing_channel",
        "underperforming_channel",
    }
    assert len(forecasting["recommendations"]) >= 2
    assert set(data["memory"]) == {"forecast_snapshot", "learning_signal", "backend_storage_notes"}


def test_forecast_endpoint_accepts_dynamic_payload_shape(monkeypatch):
    monkeypatch.setenv("OPENAI_ENABLED", "false")
    client = TestClient(app)
    payload = {
        "user_id": "dynamic-user",
        "forecast_type": "monthly",
        "sales_data": {
            "units_sold": 900,
            "last_period_sales": 750,
            "average_daily_sales": 30,
        },
        "stock_data": {
            "available_stock": 300,
            "minimum_stock": 120,
            "supplier_lead_time": 8,
        },
        "marketplaces": {
            "amazon": {"units": 500, "previous_units": 480},
            "shopify": {"units": 250, "previous_units": 180},
            "tiktok": {"units": 150, "previous_units": 90},
        },
        "forecast_history": [
            {"trend": "increasing", "confidence_score": 0.76, "stockout_prediction_days": 12},
        ],
        "historical_accuracy": {
            "average_error": 0.18,
        },
        "historical_trends": {
            "trend": "increasing",
            "channel_bias": {"tiktok": "previously overestimated"},
        },
    }

    response = client.post("/forecast", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert set(data) == {"forecasting", "memory"}
    assert data["forecasting"]["trend"] == "increasing"
    assert data["forecasting"]["channel_insights"]["top_channel"] == "amazon"
    assert data["forecasting"]["recommendations"]
    assert data["memory"]["learning_signal"]["historical_avg_error"] == 0.18
