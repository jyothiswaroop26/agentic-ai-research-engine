from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.config import Settings, get_settings
from app.services.ai_service import AIService


router = APIRouter(prefix="/api", tags=["ai"])


class PromptRequest(BaseModel):
	prompt: str = Field(min_length=1)
	model: str | None = None


class PromptResponse(BaseModel):
	response: str
	model: str


class ConnectivityResponse(BaseModel):
	status: str


def get_ai_service(settings: Settings = Depends(get_settings)) -> AIService:
	return AIService(settings)


@router.get("/health", response_model=ConnectivityResponse)
def health() -> ConnectivityResponse:
	return ConnectivityResponse(status="ok")


@router.get("/openai/connectivity", response_model=ConnectivityResponse)
def openai_connectivity(service: AIService = Depends(get_ai_service)) -> ConnectivityResponse:
	try:
		if service.verify_connectivity():
			return ConnectivityResponse(status="connected")
	except Exception as exc:
		raise HTTPException(status_code=503, detail=f"OpenAI connectivity failed: {exc}") from exc

	raise HTTPException(status_code=503, detail="OpenAI connectivity failed")


@router.post("/llm/respond", response_model=PromptResponse)
def llm_respond(payload: PromptRequest, service: AIService = Depends(get_ai_service)) -> PromptResponse:
	try:
		text = service.generate_text(prompt=payload.prompt, model=payload.model)
		return PromptResponse(response=text, model=payload.model or service.settings.openai_model)
	except Exception as exc:
		raise HTTPException(status_code=500, detail=f"LLM response generation failed: {exc}") from exc
