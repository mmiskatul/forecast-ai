import json
from pathlib import Path
from typing import Any

from app.core.config import get_settings
from app.schemas import ForecastInput, ForecastOutput


class OpenAIForecastError(RuntimeError):
    pass


def load_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


class OpenAIForecastService:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.enabled = self.settings.openai_enabled and bool(self.settings.openai_api_key)
        self.client = None
        if self.enabled:
            try:
                from openai import AsyncOpenAI
            except ImportError as exc:
                raise OpenAIForecastError("OpenAI package is not installed.") from exc

            self.client = AsyncOpenAI(api_key=self.settings.openai_api_key)
        self.root = Path(__file__).resolve().parents[2]

    async def generate(self, payload: ForecastInput) -> ForecastOutput:
        if not self.enabled or self.client is None:
            raise OpenAIForecastError("OpenAI is disabled.")

        system_prompt = load_text(self.root / "prompts" / "system-prompt.md")
        output_schema = load_json(self.root / "schemas" / "output.schema.json")

        try:
            response = await self.client.responses.create(
                model=self.settings.openai_model,
                input=[
                    {"role": "system", "content": system_prompt},
                    {
                        "role": "user",
                        "content": json.dumps(payload.model_dump(mode="json"), ensure_ascii=False),
                    },
                ],
                text={
                    "format": {
                        "type": "json_schema",
                        "name": "forecast_ai_output",
                        "schema": output_schema,
                        "strict": True,
                    }
                },
            )
        except Exception as exc:  # pragma: no cover - provider/network failure
            raise OpenAIForecastError(str(exc)) from exc

        output_text = (response.output_text or "").strip()
        if not output_text:
            raise OpenAIForecastError("OpenAI returned an empty response.")

        try:
            parsed = json.loads(output_text)
            return ForecastOutput.model_validate(parsed)
        except Exception as exc:
            raise OpenAIForecastError("OpenAI returned invalid forecast JSON.") from exc
