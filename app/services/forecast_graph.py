from typing import Any, TypedDict

from app.schemas import ForecastInput, ForecastOutput
from app.services.forecast_engine import generate_forecast, normalize_current_data, normalize_memory
from app.services.openai_forecast_service import OpenAIForecastError, OpenAIForecastService


class ForecastGraphState(TypedDict, total=False):
    payload: ForecastInput
    current_data: dict[str, Any]
    memory_data: dict[str, Any]
    memory_analysis: dict[str, Any]
    openai_result: ForecastOutput
    result: ForecastOutput
    error: str


def build_forecast_graph():
    from langgraph.graph import END, START, StateGraph

    graph = StateGraph(ForecastGraphState)

    async def normalize_input(state: ForecastGraphState) -> ForecastGraphState:
        payload = state["payload"]
        return {
            **state,
            "current_data": normalize_current_data(payload),
            "memory_data": normalize_memory(payload),
        }

    async def analyze_memory(state: ForecastGraphState) -> ForecastGraphState:
        memory_data = state.get("memory_data", {})
        previous_forecasts = memory_data.get("previous_forecasts", [])
        forecast_accuracy = memory_data.get("forecast_accuracy", {})
        user_trends = memory_data.get("user_trends", {})

        return {
            **state,
            "memory_analysis": {
                "previous_forecast_count": len(previous_forecasts),
                "has_accuracy_history": bool(forecast_accuracy),
                "has_user_trends": bool(user_trends),
                "memory_available": bool(previous_forecasts or forecast_accuracy or user_trends),
            },
        }

    async def openai_forecast(state: ForecastGraphState) -> ForecastGraphState:
        try:
            openai_result = await OpenAIForecastService().generate(state["payload"])
            openai_result.memory.learning_signal["graph_model_source"] = "openai"
            return {**state, "openai_result": openai_result}
        except OpenAIForecastError as exc:
            return {**state, "error": str(exc)}

    async def finalize_forecast(state: ForecastGraphState) -> ForecastGraphState:
        result = state.get("openai_result")

        if result is None:
            result = generate_forecast(state["payload"])
            result.memory.learning_signal["graph_model_source"] = "deterministic_fallback"

        result.memory.learning_signal["langgraph_workflow"] = [
            "normalize_input",
            "analyze_memory",
            "openai_forecast",
            "finalize_forecast",
        ]
        result.memory.learning_signal["memory_analysis"] = state.get("memory_analysis", {})

        if state.get("error"):
            result.memory.learning_signal["fallback_reason"] = state["error"]

        return {**state, "result": result}

    graph.add_node("normalize_input", normalize_input)
    graph.add_node("analyze_memory", analyze_memory)
    graph.add_node("openai_forecast", openai_forecast)
    graph.add_node("finalize_forecast", finalize_forecast)

    graph.add_edge(START, "normalize_input")
    graph.add_edge("normalize_input", "analyze_memory")
    graph.add_edge("analyze_memory", "openai_forecast")
    graph.add_edge("openai_forecast", "finalize_forecast")
    graph.add_edge("finalize_forecast", END)

    return graph.compile()


async def run_forecast_graph(payload: ForecastInput) -> ForecastOutput:
    compiled_graph = build_forecast_graph()
    state = await compiled_graph.ainvoke({"payload": payload})
    return state["result"]
