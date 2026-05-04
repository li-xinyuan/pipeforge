from fastapi import APIRouter
from configforge.models.ai import AiSuggestionRequest, AiSuggestionResponse

router = APIRouter()


@router.post("/suggest", response_model=AiSuggestionResponse)
async def suggest(req: AiSuggestionRequest):
    # v0.1: AI backend is optional; return no-op response if not configured
    return AiSuggestionResponse(content="AI 未配置，请手动填写", category=req.category)
