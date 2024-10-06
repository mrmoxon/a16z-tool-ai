from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from app.models.chat_model import ChatMessage
from app.services.chat_service import chat_service
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/chat")
async def chat(message: ChatMessage):
    try:
        logger.info(f"Received request to /chat with message: {message.message}")
        return StreamingResponse(chat_service.generate_response(message), media_type="text/event-stream")
    except HTTPException as he:
        logger.error(f"HTTP exception in /chat endpoint: {str(he)}", exc_info=True)
        raise he
    except Exception as e:
        logger.error(f"Unexpected error in /chat endpoint: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")

@router.post("/chat/{conversation_id}")
async def chat_with_history(conversation_id: str, message: ChatMessage):
    try:
        logger.info(f"Received request for conversation ID: {conversation_id}")
        return StreamingResponse(chat_service.generate_response(message, conversation_id), media_type="text/event-stream")
    except HTTPException as he:
        logger.error(f"HTTP exception in /chat/{{conversation_id}} endpoint: {str(he)}", exc_info=True)
        raise he
    except Exception as e:
        logger.error(f"Unexpected error in /chat/{{conversation_id}} endpoint: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")

logger.info(f"Router paths: {[route.path for route in router.routes]}")