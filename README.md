# Forecast AI

Memory-aware FastAPI and LangGraph forecasting service for **Restock Radar**.

The API accepts a dynamic business payload from your backend, uses backend-provided memory, calls OpenAI `gpt-5` through a LangGraph workflow, and returns two top-level objects:

- `forecasting`: data to show on the frontend
- `memory`: data your backend should store user-wise/store-wise for future learning

## Tech Stack

- Python 3.13
- FastAPI
- Uvicorn
- LangGraph
- OpenAI Responses API
- Pydantic
- Docker

## Folder Structure

```text
forecast-ai/
  app/
    main.py                         FastAPI routes
    config.py                       .env configuration
    schemas.py                      request/response models
    services/
      forecast_graph.py             LangGraph workflow
      openai_forecast_service.py    OpenAI gpt-5 structured output call
      forecast_engine.py            deterministic fallback forecast engine
  examples/
    sample-input.json               sample request body
  prompts/
    system-prompt.md                forecasting system prompt
  schemas/
    input.schema.json               public input schema reference
    output.schema.json              strict OpenAI/response JSON schema
  tests/
    test_forecast_engine.py
  Dockerfile
  docker-compose.yml
  requirements.txt
  .env
```

## Flow

```text
POST /forecast
  -> FastAPI receives dynamic backend payload
  -> LangGraph normalize_input node extracts sales, inventory, channels, memory
  -> LangGraph analyze_memory node checks history, accuracy, trends, bias
  -> LangGraph openai_forecast node calls OpenAI gpt-5 with strict JSON schema
  -> LangGraph finalize_forecast node returns OpenAI result or deterministic fallback
  -> API returns { forecasting, memory }
```

## Environment

Create `.env` in this folder:

```text
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_MODEL=gpt-5
OPENAI_ENABLED=true
```

You can copy the template:

```bat
copy .env.example .env
```

Do not commit `.env`. It is already ignored by `.gitignore` and `.dockerignore`.

## Run Locally

```bat
cd C:\Miskat\siyam\forecast-ai
python -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --reload --port 8010
```

Open:

```text
http://localhost:8010/docs
```

Health check:

```text
http://localhost:8010/
http://localhost:8010/health
```

## Run With Docker

Build the image:

```bat
cd C:\Miskat\siyam\forecast-ai
docker build -t forecast-ai .
```

Run the container:

```bat
docker run --rm --env-file .env -p 8010:8010 forecast-ai
```

Open:

```text
http://localhost:8010/docs
```

## Run With Docker Compose

```bat
cd C:\Miskat\siyam\forecast-ai
docker compose up --build
```

Stop:

```bat
docker compose down
```

## Get A Forecast Response

PowerShell:

```powershell
$body = @'
{
  "current_data": {
    "sales_data": {
      "units_sold": 850,
      "last_period_sales": 700,
      "average_daily_sales": 42
    },
    "stock_data": {
      "available_stock": 360,
      "minimum_stock": 150,
      "supplier_lead_time": 7
    },
    "marketplaces": {
      "amazon": {
        "units": 420,
        "previous_units": 390
      },
      "shopify": {
        "units": 210,
        "previous_units": 180
      },
      "tiktok": {
        "units": 220,
        "previous_units": 130
      }
    }
  },
  "memory": {
    "forecast_history": [
      {
        "trend": "increasing",
        "confidence_score": 0.78,
        "stockout_prediction_days": 12
      }
    ],
    "historical_accuracy": {
      "average_error": 0.11
    },
    "historical_trends": {
      "trend": "increasing",
      "channel_bias": {
        "tiktok": "previously overestimated",
        "amazon": "stable"
      }
    }
  }
}
'@

Invoke-RestMethod `
  -Uri "http://localhost:8010/forecast" `
  -Method Post `
  -ContentType "application/json" `
  -Body $body
```

curl:

```bash
curl -X POST "http://localhost:8010/forecast" \
  -H "Content-Type: application/json" \
  -d @examples/sample-input.json
```

Expected response shape:

```json
{
  "forecasting": {
    "trend": "increasing",
    "demand_level": "high",
    "risk_level": "medium",
    "confidence_score": 0.9,
    "stockout_prediction_days": 9,
    "forecast_summary": "string",
    "learning_notes": "string",
    "channel_insights": {
      "top_channel": "amazon",
      "fastest_growing_channel": "tiktok",
      "underperforming_channel": "shopify"
    },
    "recommendations": [
      "string",
      "string"
    ]
  },
  "memory": {
    "forecast_snapshot": {},
    "learning_signal": {},
    "backend_storage_notes": "string"
  }
}
```

## Test

```bat
cd C:\Miskat\siyam\forecast-ai
.venv\Scripts\activate
python -m pytest
```
