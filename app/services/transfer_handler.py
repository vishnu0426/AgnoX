import asyncio
import asyncpg
import logging
from datetime import datetime
from typing import Dict, Optional
from livekit import api

logger = logging.getLogger(__name__)


class TransferHandler:
    """Handles call transfers between AI and human agents"""
    
    def __init__(self, livekit_api: api.LiveKitAPI, db_pool: asyncpg.Pool):
        self.api = livekit_api
        self.db_pool = db_pool
    
    async def cold_transfer(
        self, 
        room_name: str,
        agent_phone: str,
        sip_trunk_id: str
    ) -> Dict:
        """
        Cold transfer - Direct transfer to human agent
        AI disconnects immediately
        
        Args:
            room_name: Current room name
            agent_phone: Human agent phone number
            sip_trunk_id: SIP trunk ID
            
        Returns:
            Transfer result
        """
        try:
            logger.info(f"Initiating cold transfer to {agent_phone}")
            
            # Get customer participant
            participants = await self.api.room.list_participants(
                api.ListParticipantsRequest(room=room_name)
            )
            
            customer_participant = None
            for p in participants:
                if "sip" in p.identity.lower():
                    customer_participant = p
                    break
            
            if not customer_participant:
                logger.error("No customer participant found")
                return {"success": False, "error": "No customer found"}
            
            # Transfer using SIP REFER
            await self.api.sip.transfer_sip_participant(
                api.TransferSIPParticipantRequest(
                    room_name=room_name,
                    participant_identity=customer_participant.identity,
                    transfer_to=agent_phone
                )
            )
            
            logger.info(f"Cold transfer completed to {agent_phone}")
            return {
                "success": True,
                "type": "cold",
                "agent_phone": agent_phone
            }
            
        except Exception as e:
            logger.error(f"Cold transfer failed: {e}")
            return {"success": False, "error": str(e)}
    
    async def warm_transfer(
        self,
        caller_room: str,
        agent_phone: str,
        sip_trunk_id: str,
        conversation_context: str,
        session_id: int
    ) -> Dict:
        """
        Warm transfer - AI briefs human agent before connecting customer
        
        Args:
            caller_room: Customer's current room
            agent_phone: Human agent phone number
            sip_trunk_id: SIP trunk ID
            conversation_context: Summary of conversation so far
            session_id: Call session ID
            
        Returns:
            Transfer result
        """
        try:
            logger.info(f"Initiating warm transfer to {agent_phone}")
            
            # Step 1: Create consultation room for AI + Human agent
            consultation_room = f"consult-{session_id}"
            
            # Step 2: Dial human agent into consultation room
            logger.info(f"Dialing agent {agent_phone} into consultation room")
            
            sip_participant = await self.api.sip.create_sip_participant(
                api.CreateSIPParticipantRequest(
                    sip_trunk_id=sip_trunk_id,
                    sip_call_to=agent_phone,
                    room_name=consultation_room,
                    participant_identity=f"agent-{agent_phone}",
                    participant_name="Human Agent",
                    participant_metadata=conversation_context
                )
            )
            
            # Step 3: Wait for agent to answer
            await asyncio.sleep(3)
            
            logger.info(f"Warm transfer initiated to {agent_phone}")
            return {
                "success": True,
                "type": "warm",
                "agent_phone": agent_phone,
                "consultation_room": consultation_room
            }
            
        except Exception as e:
            logger.error(f"Warm transfer failed: {e}")
            return {"success": False, "error": str(e)}
    
    async def log_transfer(
        self,
        session_id: int,
        agent_id: int,
        transfer_type: str,
        success: bool
    ):
        """Log transfer attempt to database"""
        async with self.db_pool.acquire() as conn:
            try:
                await conn.execute(
                    """
                    UPDATE call_sessions
                    SET agent_id = $1,
                        handled_by = 'human',
                        transfer_count = transfer_count + 1,
                        call_metadata = call_metadata || $2::jsonb
                    WHERE session_id = $3
                    """,
                    agent_id,
                    {
                        "transfer_type": transfer_type,
                        "transfer_success": success,
                        "transfer_time": datetime.now().isoformat()
                    },
                    session_id
                )
                logger.info(f"Logged transfer for session {session_id}")
            except Exception as e:
                logger.error(f"Error logging transfer: {e}")