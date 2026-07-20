from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.config import Settings, get_settings
from app.services.ai_service import AIService
from app.services.report_service import ReportService
from app.agents.report_writer import ReportAgent, create_report_agent


router = APIRouter(prefix="/api", tags=["ai"])


class PromptRequest(BaseModel):
	prompt: str = Field(min_length=1)
	model: str | None = None


class PromptResponse(BaseModel):
	response: str
	model: str


class ConnectivityResponse(BaseModel):
	status: str


class ReportValidationRequest(BaseModel):
	report: str = Field(description="Report content to validate")
	format_type: str = Field(default="markdown", description="Report format: 'markdown' or 'html'")


class ReportValidationResponse(BaseModel):
	is_valid: bool
	format: str | None = None
	length: int | None = None
	issues: list[str]
	warnings: list[str] | None = None


def get_ai_service(settings: Settings = Depends(get_settings)) -> AIService:
	return AIService(settings)


def get_report_agent() -> ReportAgent:
	"""Dependency to provide a ReportAgent instance."""
	return create_report_agent()


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


@router.post("/reports/validate", response_model=ReportValidationResponse)
def validate_report(payload: ReportValidationRequest) -> ReportValidationResponse:
	"""Validate a report for completeness and correctness."""
	try:
		report_service = ReportService()
		result = report_service.validate_report(payload.report, format_type=payload.format_type)
		return ReportValidationResponse(
			is_valid=result["is_valid"],
			format=result.get("format"),
			length=result.get("length"),
			issues=result.get("issues", []),
			warnings=result.get("warnings"),
		)
	except Exception as exc:
		raise HTTPException(status_code=400, detail=f"Report validation failed: {exc}") from exc
