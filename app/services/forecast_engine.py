from collections import Counter
from math import ceil
from typing import Any

from app.schemas import ChannelInsights, ForecastInput, ForecastOutput, ForecastingResult, MemoryResult


def number_or_zero(value: Any) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return 0

    return number


def clamp(value: float, minimum: float, maximum: float) -> float:
    return min(max(value, minimum), maximum)


def most_common(values: list[str | None]) -> str | None:
    filtered = [value for value in values if value]
    if not filtered:
        return None

    return Counter(filtered).most_common(1)[0][0]


def first_dict(source: dict[str, Any], keys: list[str]) -> dict[str, Any]:
    for key in keys:
        value = source.get(key)
        if isinstance(value, dict):
            return value

    return {}


def first_list(source: dict[str, Any], keys: list[str]) -> list[dict[str, Any]]:
    for key in keys:
        value = source.get(key)
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]

    return []


def first_number(source: dict[str, Any], keys: list[str]) -> float:
    for key in keys:
        if key in source:
            number = number_or_zero(source.get(key))
            if number != 0:
                return number

    return 0


def normalize_current_data(payload: ForecastInput) -> dict[str, Any]:
    raw = payload.model_dump()
    current_data = payload.current_data if isinstance(payload.current_data, dict) else {}
    merged = {**raw, **current_data}

    sales = first_dict(
        merged,
        ["sales", "sales_data", "orders", "order_data", "demand", "metrics", "revenue"],
    )
    inventory = first_dict(
        merged,
        ["inventory", "inventory_data", "stock", "stock_data", "warehouse", "products"],
    )
    channels = first_dict(
        merged,
        ["channels", "channel_data", "marketplaces", "platforms", "stores"],
    )

    if not sales:
        sales = merged

    if not inventory:
        inventory = merged

    return {
        "sales": sales,
        "inventory": inventory,
        "channels": channels,
    }


def normalize_memory(payload: ForecastInput) -> dict[str, Any]:
    raw = payload.model_dump()
    memory = payload.memory if isinstance(payload.memory, dict) else {}
    merged = {**raw, **memory}

    forecast_accuracy = first_dict(
        merged,
        ["forecast_accuracy", "accuracy", "historical_accuracy", "forecast_metrics"],
    )
    user_trends = first_dict(
        merged,
        ["user_trends", "trends", "historical_trends", "behavior", "memory_trends"],
    )
    previous_forecasts = first_list(
        merged,
        ["previous_forecasts", "forecasts", "history", "forecast_history", "past_predictions"],
    )

    return {
        "previous_forecasts": previous_forecasts,
        "forecast_accuracy": forecast_accuracy,
        "user_trends": user_trends,
    }


def channel_entries(channels: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    entries = []

    for name, data in channels.items():
        sales = number_or_zero(data.get("sales_units", data.get("sales", data.get("units"))))
        previous_sales = number_or_zero(
            data.get("previous_sales_units", data.get("previous_sales", data.get("previous_units")))
        )
        growth_rate = (sales - previous_sales) / previous_sales if previous_sales > 0 else 1 if sales > 0 else 0

        entries.append(
            {
                "name": name,
                "sales": sales,
                "previous_sales": previous_sales,
                "growth_rate": growth_rate,
            }
        )

    return entries


def detect_trend(
    current_sales: float,
    previous_sales: float,
    previous_forecasts: list[dict[str, Any]],
    memory_trend: str | None,
) -> str:
    sales_growth = (current_sales - previous_sales) / previous_sales if previous_sales > 0 else 0
    previous_trend = most_common([forecast.get("trend") for forecast in previous_forecasts])

    if sales_growth > 0.12:
        return "increasing"

    if sales_growth < -0.12:
        return "declining"

    if previous_trend and previous_trend == memory_trend:
        return previous_trend

    return "stable"


def calculate_confidence(
    avg_error: float,
    trend: str,
    previous_forecasts: list[dict[str, Any]],
    memory_trend: str | None,
) -> float:
    if previous_forecasts:
        previous_confidence = sum(number_or_zero(item.get("confidence_score")) for item in previous_forecasts)
        confidence = previous_confidence / len(previous_forecasts)
    else:
        confidence = 0.72

    if avg_error > 0.15:
        confidence -= 0.12
    elif avg_error > 0:
        confidence += 0.08

    previous_trend = most_common([forecast.get("trend") for forecast in previous_forecasts])
    if previous_trend and previous_trend == trend and memory_trend == trend:
        confidence += 0.07

    return round(clamp(confidence, 0.35, 0.95), 2)


def apply_memory_smoothing(raw_daily_average: float, avg_error: float, previous_forecasts: list[dict[str, Any]]) -> float:
    if avg_error <= 0.15 or not previous_forecasts:
        return raw_daily_average

    previous_stockout_days = [
        number_or_zero(forecast.get("stockout_prediction_days"))
        for forecast in previous_forecasts
        if number_or_zero(forecast.get("stockout_prediction_days")) > 0
    ]

    if not previous_stockout_days:
        return raw_daily_average * 0.9

    return raw_daily_average * 0.85


def demand_level(trend: str, daily_average_units: float, stockout_days: int) -> str:
    if trend == "increasing" and (daily_average_units >= 50 or stockout_days <= 7):
        return "high"

    if trend == "declining" and daily_average_units < 20:
        return "low"

    return "medium"


def risk_level(stockout_days: int, reorder_point: float, current_stock: float) -> str:
    if stockout_days <= 5 or current_stock <= reorder_point:
        return "high"

    if stockout_days <= 14 or current_stock <= reorder_point * 1.5:
        return "medium"

    return "low"


def detect_channel_insights(
    channels: list[dict[str, Any]],
    channel_bias: dict[str, str],
) -> ChannelInsights:
    if not channels:
        return ChannelInsights(
            top_channel="unknown",
            fastest_growing_channel="unknown",
            underperforming_channel="unknown",
        )

    adjusted = []
    for channel in channels:
        bias = channel_bias.get(channel["name"], "").lower()
        growth_penalty = 0.15 if "overestimated" in bias else 0
        adjusted.append({**channel, "adjusted_growth_rate": channel["growth_rate"] - growth_penalty})

    top_channel = max(adjusted, key=lambda channel: channel["sales"])
    fastest_growing = max(adjusted, key=lambda channel: channel["adjusted_growth_rate"])
    underperforming = min(adjusted, key=lambda channel: channel["adjusted_growth_rate"])

    return ChannelInsights(
        top_channel=top_channel["name"],
        fastest_growing_channel=fastest_growing["name"],
        underperforming_channel=underperforming["name"],
    )


def generate_forecast(payload: ForecastInput) -> ForecastOutput:
    current_data = normalize_current_data(payload)
    memory = normalize_memory(payload)
    sales = current_data["sales"]
    inventory = current_data["inventory"]
    previous_forecasts = memory["previous_forecasts"]
    avg_error = first_number(memory["forecast_accuracy"], ["avg_error", "average_error", "error_rate", "mape"])
    memory_trend = memory["user_trends"].get("growth_pattern") or memory["user_trends"].get("trend")
    channel_bias = memory["user_trends"].get("channel_bias", {})
    if not isinstance(channel_bias, dict):
        channel_bias = {}

    total_sales = first_number(
        sales,
        ["total_units", "current_total_units", "units_sold", "total_sales", "sales_units", "quantity_sold"],
    )
    previous_total_sales = first_number(
        sales,
        ["previous_total_units", "previous_units_sold", "previous_total_sales", "last_period_sales"],
    )
    raw_daily_average = first_number(
        sales,
        ["daily_average_units", "daily_avg_units", "average_daily_sales", "daily_sales"],
    ) or total_sales / 7 or 1
    daily_average_units = apply_memory_smoothing(raw_daily_average, avg_error, previous_forecasts)

    current_stock = first_number(
        inventory,
        ["current_stock", "stock_on_hand", "available_stock", "inventory_units", "quantity_available"],
    )
    reorder_point = first_number(inventory, ["reorder_point", "reorder_level", "minimum_stock", "safety_stock"])
    lead_time_days = int(first_number(inventory, ["lead_time_days", "lead_time", "supplier_lead_time"]) or 5)
    stockout_days = ceil(current_stock / max(daily_average_units, 1)) if current_stock > 0 else 0

    trend = detect_trend(total_sales, previous_total_sales, previous_forecasts, memory_trend)
    confidence_score = calculate_confidence(avg_error, trend, previous_forecasts, memory_trend)
    demand = demand_level(trend, daily_average_units, stockout_days)
    risk = risk_level(stockout_days, reorder_point, current_stock)
    insights = detect_channel_insights(channel_entries(current_data["channels"]), channel_bias)

    if avg_error > 0.15:
        learning_notes = "Memory showed forecast error above 15%, so predictions were smoothed and confidence was reduced."
    else:
        learning_notes = (
            "Memory showed acceptable forecast accuracy, so trend consistency and channel history increased "
            "prediction confidence."
        )

    recommendations = [
        (
            f"Reorder immediately because projected stockout is within {stockout_days} days."
            if risk == "high"
            else f"Monitor stock closely and reorder before the {lead_time_days}-day lead time window."
        ),
        (
            f"Prioritize inventory allocation for {insights.fastest_growing_channel}."
            if insights.fastest_growing_channel != "unknown"
            else "Collect channel-level sales history to improve future forecasts."
        ),
    ]

    if avg_error > 0.15:
        recommendations.append("Review recent actual-vs-predicted errors before increasing purchase orders.")

    forecasting = ForecastingResult(
        trend=trend,
        demand_level=demand,
        risk_level=risk,
        confidence_score=confidence_score,
        stockout_prediction_days=stockout_days,
        forecast_summary=f"Demand is {trend} with {demand} demand and {risk} inventory risk.",
        learning_notes=learning_notes,
        channel_insights=insights,
        recommendations=recommendations,
    )

    memory_result = MemoryResult(
        forecast_snapshot={
            "trend": trend,
            "demand_level": demand,
            "risk_level": risk,
            "confidence_score": confidence_score,
            "stockout_prediction_days": stockout_days,
            "channel_insights": insights.model_dump(),
        },
        learning_signal={
            "used_previous_forecasts": len(previous_forecasts),
            "historical_avg_error": avg_error,
            "memory_trend": memory_trend,
            "smoothing_applied": avg_error > 0.15 and bool(previous_forecasts),
            "channel_bias_used": bool(channel_bias),
        },
        backend_storage_notes=(
            "Store this memory object under the authenticated user or store record in the backend database. "
            "Compare forecast_snapshot against future actual results to update accuracy and error patterns."
        ),
    )

    return ForecastOutput(forecasting=forecasting, memory=memory_result)
