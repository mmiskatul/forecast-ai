# Forecast AI Structure

```text
app/
  api/        FastAPI routes
  core/       settings and exception handlers
  graphs/     LangGraph forecasting workflow
  schemas/    Pydantic request/response models
  services/   deterministic engine and OpenAI service
  main.py     app setup
```

Compatibility shim modules remain at `app/config.py`, `app/exceptions.py`, and
`app/services/forecast_graph.py` so older imports still work while new code uses
the structured packages.
