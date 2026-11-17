"OpenAI-compatible chat completion provider adapter."
import httpx

from app.config.settings import get_settings


class ProviderNotConfigured(RuntimeError):
    """LLM endpoint credentials are missing."""


class OpenAICompatibleProvider:
    provider_name = "openai-compatible"

    def __init__(self, base_url: str, api_key: str, model: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model

    @classmethod
    def from_settings(cls) -> "OpenAICompatibleProvider":
        settings = get_settings()
        if not settings.llm_base_url or not settings.llm_api_key or not settings.llm_model:
            raise ProviderNotConfigured(
                "PIMS_LLM_BASE_URL, PIMS_LLM_API_KEY and PIMS_LLM_MODEL must be set"
            )
        return cls(settings.llm_base_url, settings.llm_api_key, settings.llm_model)

    def generate(self, system: str, user: str) -> str:
        response = httpx.post(
            f"{self.base_url}/chat/completions",
            headers={"Authorization": f"Bearer {self.api_key}"},
            json={
                "model": self.model,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                "temperature": 0.2,
            },
            timeout=120.0,
        )
        response.raise_for_status()
        payload = response.json()
        return payload["choices"][0]["message"]["content"]
