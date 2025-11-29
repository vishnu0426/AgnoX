import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, Field
import asyncpg

from app.api.dependencies import get_db_pool, verify_token
from app.api.schemas.call_schema import (
    CallSessionResponse,
    CallListResponse,
    TransferRequest,
    TransferResponse,
    TranscriptEntry
)
from app.services.customer_service import CustomerService
from app.services.transfer_handler import TransferHandler
from app.services.transcript_service import TranscriptService
from app.sip.outbound_call_manager import OutboundCallManager
from config.livekit_config import livekit_config
from config.settings import settings

logger = logging.getLogger(__name__)
router = APIRouter()


# ==================== PYDANTIC SCHEMAS ====================

class OutboundCallRequest(BaseModel):
    """Request schema for creating outbound call"""
    to_number: str = Field(..., description="Destination phone number (E.164 format)")
    from_number: Optional[str] = Field(None, description="Caller ID number (uses default if not provided)")
    trunk_id: Optional[str] = Field(None, description="Outbound trunk ID (uses default if not provided)")
    customer_id: Optional[int] = Field(None, description="Customer database ID if known")
    metadata: Optional[dict] = Field(default_factory=dict, description="Additional call metadata")
    play_ringtone: bool = Field(True, description="Play ringtone while connecting")


class OutboundCallResponse(BaseModel):
    """Response schema for outbound call creation"""
    success: bool
    sip_call_id: str
    participant_id: str
    room_name: str
    to_number: str
    from_number: str
    status: str
    message: str


class CallbackRequest(BaseModel):
    """Request schema for scheduling callback"""
    customer_phone: str = Field(..., description="Customer phone number")
    customer_id: Optional[int] = Field(None, description="Customer database ID")
    reason: Optional[str] = Field(None, description="Reason for callback")
    from_number: Optional[str] = Field(None, description="Caller ID (uses default if not provided)")
    metadata: Optional[dict] = Field(default_factory=dict)


class BatchCallRequest(BaseModel):
    """Request schema for batch calls"""
    calls: List[dict] = Field(..., description="List of calls with 'to_number' and optional 'metadata'")
    from_number: Optional[str] = Field(None, description="Caller ID")
    trunk_id: Optional[str] = Field(None, description="Outbound trunk ID")
    delay_seconds: int = Field(2, description="Delay between calls", ge=1, le=10)


class BatchCallResponse(BaseModel):
    """Response schema for batch calls"""
    total: int
    successful: int
    failed: int
    results: List[dict]


# ==================== INBOUND CALL ENDPOINTS ====================

@router.get("/calls/inbound/active", response_model=CallListResponse)
async def get_active_inbound_calls(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    db_pool: asyncpg.Pool = Depends(get_db_pool),
    token: str = Depends(verify_token)
):
    """
    Get all active inbound calls
    
    Returns paginated list of active inbound call sessions
    """
    try:
        offset = (page - 1) * page_size
        
        async with db_pool.acquire() as conn:
            calls = await conn.fetch(
                """
                SELECT session_id, customer_id, room_name, start_time,
                       end_time, duration_seconds, handled_by, sentiment, transfer_count
                FROM call_sessions
                WHERE end_time IS NULL
                ORDER BY start_time DESC
                LIMIT $1 OFFSET $2
                """,
                page_size,
                offset
            )
            
            total = await conn.fetchval(
                "SELECT COUNT(*) FROM call_sessions WHERE end_time IS NULL"
            )
            
            return CallListResponse(
                calls=[CallSessionResponse(**dict(call)) for call in calls],
                total=total,
                page=page,
                page_size=page_size
            )
    except Exception as e:
        logger.error(f"Failed to get active inbound calls: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve active inbound calls"
        )


@router.get("/calls/inbound/{session_id}", response_model=CallSessionResponse)
async def get_inbound_call_details(
    session_id: int,
    db_pool: asyncpg.Pool = Depends(get_db_pool),
    token: str = Depends(verify_token)
):
    """
    Get inbound call session details
    
    Args:
        session_id: Call session ID
        
    Returns:
        Call session details
    """
    try:
        async with db_pool.acquire() as conn:
            call = await conn.fetchrow(
                """
                SELECT session_id, customer_id, room_name, start_time,
                       end_time, duration_seconds, handled_by, sentiment, transfer_count
                FROM call_sessions
                WHERE session_id = $1
                """,
                session_id
            )
            
            if not call:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Call session not found"
                )
            
            return CallSessionResponse(**dict(call))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get inbound call details: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve call details"
        )


# ==================== OUTBOUND CALL ENDPOINTS ====================

@router.post("/calls/outbound/create", response_model=OutboundCallResponse)
async def create_outbound_call(
    request: OutboundCallRequest,
    db_pool: asyncpg.Pool = Depends(get_db_pool),
    token: str = Depends(verify_token)
):
    """
    Create an outbound call
    
    Args:
        request: Outbound call request with destination number
        
    Returns:
        Outbound call details including SIP call ID
    """
    try:
        # Use default values from settings if not provided
        from_number = request.from_number or settings.default_caller_id
        trunk_id = request.trunk_id or settings.default_outbound_trunk_id
        
        if not from_number:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="from_number must be provided or DEFAULT_CALLER_ID must be set"
            )
        
        if not trunk_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="trunk_id must be provided or DEFAULT_OUTBOUND_TRUNK_ID must be set"
            )
        
        # Initialize outbound call manager
        outbound_manager = OutboundCallManager(db_pool)
        
        # Add customer_id to metadata if provided
        metadata = request.metadata or {}
        if request.customer_id:
            metadata["customer_id"] = request.customer_id
        
        # Create the outbound call
        call_info = await outbound_manager.create_outbound_call(
            to_number=request.to_number,
            from_number=from_number,
            trunk_id=trunk_id,
            metadata=metadata,
            play_ringtone=request.play_ringtone
        )
        
        logger.info(f"Outbound call created: sip_call_id={call_info['sip_call_id']}")
        
        return OutboundCallResponse(
            success=True,
            sip_call_id=call_info["sip_call_id"],
            participant_id=call_info["participant_id"],
            room_name=call_info["room_name"],
            to_number=call_info["to_number"],
            from_number=call_info["from_number"],
            status=call_info["status"],
            message=f"Outbound call initiated to {request.to_number}"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create outbound call: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create outbound call: {str(e)}"
        )


@router.post("/calls/outbound/callback", response_model=OutboundCallResponse)
async def create_callback(
    request: CallbackRequest,
    db_pool: asyncpg.Pool = Depends(get_db_pool),
    token: str = Depends(verify_token)
):
    """
    Initiate a callback to a customer
    
    Args:
        request: Callback request with customer phone
        
    Returns:
        Callback call details
    """
    try:
        from_number = request.from_number or settings.default_caller_id
        trunk_id = settings.default_outbound_trunk_id
        
        if not from_number or not trunk_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Default caller ID and outbound trunk must be configured"
            )
        
        outbound_manager = OutboundCallManager(db_pool)
        
        call_info = await outbound_manager.create_callback_call(
            customer_phone=request.customer_phone,
            from_number=from_number,
            trunk_id=trunk_id,
            customer_id=request.customer_id,
            reason=request.reason,
            metadata=request.metadata
        )
        
        logger.info(f"Callback created: sip_call_id={call_info['sip_call_id']}")
        
        return OutboundCallResponse(
            success=True,
            sip_call_id=call_info["sip_call_id"],
            participant_id=call_info["participant_id"],
            room_name=call_info["room_name"],
            to_number=call_info["to_number"],
            from_number=call_info["from_number"],
            status=call_info["status"],
            message=f"Callback initiated to {request.customer_phone}"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create callback: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create callback: {str(e)}"
        )


@router.post("/calls/outbound/batch", response_model=BatchCallResponse)
async def create_batch_calls(
    request: BatchCallRequest,
    db_pool: asyncpg.Pool = Depends(get_db_pool),
    token: str = Depends(verify_token)
):
    """
    Create multiple outbound calls in batch
    
    Args:
        request: Batch call request with list of calls
        
    Returns:
        Batch operation results
    """
    try:
        from_number = request.from_number or settings.default_caller_id
        trunk_id = request.trunk_id or settings.default_outbound_trunk_id
        
        if not from_number or not trunk_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Default caller ID and outbound trunk must be configured"
            )
        
        if not request.calls:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No calls provided in batch request"
            )
        
        if len(request.calls) > 100:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Maximum 100 calls per batch"
            )
        
        outbound_manager = OutboundCallManager(db_pool)
        
        results = await outbound_manager.batch_create_calls(
            call_list=request.calls,
            trunk_id=trunk_id,
            from_number=from_number,
            delay_seconds=request.delay_seconds
        )
        
        successful = sum(1 for r in results if r.get("success"))
        failed = len(results) - successful
        
        logger.info(f"Batch calls completed: {successful} successful, {failed} failed")
        
        return BatchCallResponse(
            total=len(results),
            successful=successful,
            failed=failed,
            results=results
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create batch calls: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create batch calls: {str(e)}"
        )


@router.get("/calls/outbound/active")
async def get_active_outbound_calls(
    db_pool: asyncpg.Pool = Depends(get_db_pool),
    token: str = Depends(verify_token)
):
    """
    Get all active outbound calls
    
    Returns:
        List of active outbound calls
    """
    try:
        outbound_manager = OutboundCallManager(db_pool)
        active_calls = await outbound_manager.get_active_outbound_calls()
        
        return {
            "total": len(active_calls),
            "calls": active_calls
        }
        
    except Exception as e:
        logger.error(f"Failed to get active outbound calls: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve active outbound calls"
        )


# ==================== COMMON CALL ENDPOINTS ====================

@router.get("/calls/{session_id}/transcript", response_model=List[TranscriptEntry])
async def get_call_transcript(
    session_id: int,
    db_pool: asyncpg.Pool = Depends(get_db_pool),
    token: str = Depends(verify_token)
):
    """
    Get call transcript (works for both inbound and outbound)
    
    Args:
        session_id: Call session ID
        
    Returns:
        List of transcript entries
    """
    try:
        transcript_service = TranscriptService(db_pool)
        transcripts = await transcript_service.get_session_transcript(session_id)
        
        return [TranscriptEntry(**t) for t in transcripts]
    except Exception as e:
        logger.error(f"Failed to get transcript: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve transcript"
        )


@router.post("/calls/{session_id}/transfer", response_model=TransferResponse)
async def transfer_call(
    session_id: int,
    request: TransferRequest,
    db_pool: asyncpg.Pool = Depends(get_db_pool),
    token: str = Depends(verify_token)
):
    """
    Transfer call to human agent or external number
    
    Args:
        session_id: Call session ID
        request: Transfer request with agent ID or phone number
        
    Returns:
        Transfer result
    """
    try:
        async with db_pool.acquire() as conn:
            call = await conn.fetchrow(
                "SELECT room_name FROM call_sessions WHERE session_id = $1",
                session_id
            )
            
            if not call:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Call session not found"
                )
            
            agent = await conn.fetchrow(
                "SELECT phone_number FROM agents WHERE agent_id = $1",
                request.agent_id
            )
            
            if not agent:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Agent not found"
                )
            
            transfer_handler = TransferHandler(
                livekit_config.get_api_client(),
                db_pool
            )
            
            trunk_id = settings.default_outbound_trunk_id
            
            if request.transfer_type == "cold":
                result = await transfer_handler.cold_transfer(
                    call['room_name'],
                    agent['phone_number'],
                    trunk_id
                )
            else:
                result = await transfer_handler.warm_transfer(
                    call['room_name'],
                    agent['phone_number'],
                    trunk_id,
                    request.reason,
                    session_id
                )
            
            return TransferResponse(
                success=result.get('success', False),
                message=f"Call transferred to agent {request.agent_id}",
                agent_id=request.agent_id,
                transfer_type=request.transfer_type
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to transfer call: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to transfer call"
        )


@router.get("/calls/all/active")
async def get_all_active_calls(
    db_pool: asyncpg.Pool = Depends(get_db_pool),
    token: str = Depends(verify_token)
):
    """
    Get all active calls (both inbound and outbound)
    
    Returns:
        Combined list of all active calls
    """
    try:
        async with db_pool.acquire() as conn:
            # Get inbound calls
            inbound_calls = await conn.fetch(
                """
                SELECT session_id, customer_id, room_name, start_time,
                       'inbound' as call_type
                FROM call_sessions
                WHERE end_time IS NULL
                ORDER BY start_time DESC
                """
            )
            
            # Get outbound calls
            outbound_calls = await conn.fetch(
                """
                SELECT id as session_id, to_number, room_name, created_at as start_time,
                       'outbound' as call_type
                FROM outbound_calls
                WHERE status IN ('initiating', 'ringing', 'answered')
                ORDER BY created_at DESC
                """
            )
            
            return {
                "total": len(inbound_calls) + len(outbound_calls),
                "inbound_count": len(inbound_calls),
                "outbound_count": len(outbound_calls),
                "inbound_calls": [dict(call) for call in inbound_calls],
                "outbound_calls": [dict(call) for call in outbound_calls]
            }
            
    except Exception as e:
        logger.error(f"Failed to get all active calls: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve active calls"
        )