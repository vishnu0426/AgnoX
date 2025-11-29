import logging
from fastapi import APIRouter, Request, HTTPException, status
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)
router = APIRouter()


class WebhookEvent(BaseModel):
    event_type: str = Field(..., description="Event type")
    timestamp: str = Field(..., description="Event timestamp")
    data: Dict[str, Any] = Field(..., description="Event data")


@router.post("/webhooks/livekit")
async def livekit_webhook(request: Request):
    """Handle LiveKit webhook events"""
    try:
        body = await request.json()
        logger.info(f"Received LiveKit webhook: {body}")
        
        # Process webhook event
        # Add your webhook handling logic here
        
        return {"status": "received"}
    except Exception as e:
        logger.error(f"Failed to process webhook: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process webhook"
        )


@router.post("/webhooks/sip")
async def sip_webhook(request: Request):
    """Handle SIP webhook events"""
    try:
        body = await request.json()
        logger.info(f"Received SIP webhook: {body}")
        
        # Process SIP event
        # Add your SIP webhook handling logic here
        
        return {"status": "received"}
    except Exception as e:
        logger.error(f"Failed to process SIP webhook: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process webhook"
        )