from openai import OpenAI

from app.config import Settings


class AIService:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.client = OpenAI(
            api_key=settings.openai_api_key,
            base_url=settings.openai_base_url,
            timeout=settings.openai_timeout_seconds,
        )

    def generate_text(self, prompt: str, model: str | None = None) -> str:
        selected_model = model or self.settings.openai_model
        response = self.client.responses.create(
            model=selected_model,
            input=[
                {
                    "role": "user",
                    "content": [{"type": "input_text", "text": prompt}],
                }
            ],
        )
        return response.output_text

    def verify_connectivity(self) -> bool:
        self.client.models.list()
        return True
