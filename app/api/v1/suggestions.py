"""Public starter prompts for the chat empty state."""

from fastapi import APIRouter, Request

from app.schemas.envelope import ApiResponse
from app.services.suggestions import SuggestionLocale, get_suggestions

router = APIRouter(prefix="/ai", tags=["chat"])


@router.get("/suggestions", response_model=ApiResponse[list[str]])
async def suggestions(request: Request, locale: SuggestionLocale = "en-US") -> ApiResponse[list[str]]:
    return ApiResponse(data=get_suggestions(locale), requestId=request.state.request_id)
