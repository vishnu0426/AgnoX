"""
Outbound Call Manager for LiveKit Cloud
Handles initiating outbound SIP calls
Production-ready implementation
"""

import logging
import asyncio
from typing import Dict, Optional, List
from datetime import datetime
from livekit import api
from config.livekit_config import livekit_config
import asyncpg

logger = logging.getLogger(__name__)


class OutboundCallManager:
    """
    Manage outbound SIP calls through LiveKit Cloud
    Supports automated calling, callback scheduling, and outbound campaigns
    """
    
    def __init__(self, db_pool: Optional[asyncpg.Pool] = None):
        """
        Initialize outbound call manager
        
        Args:
            db_pool: Database connection pool (optional)
        """
        self.lk_api = livekit_config.get_api_client()
        self.db_pool = db_pool
        logger.info("OutboundCallManager initialized")
    
    async def create_outbound_call(
        self,
        to_number: str,
        from_number: str,
        trunk_id: str,
        room_name: Optional[str] = None,
        metadata: Optional[Dict] = None,
        play_ringtone: bool = True,
        hide_phone_number: bool = False
    ) -> Dict:
        """
        Initiate an outbound SIP call
        
        Args:
            to_number: Destination phone number (E.164 format recommended)
            from_number: Caller ID number (must be registered with trunk)
            trunk_id: Outbound SIP trunk ID to use
            room_name: LiveKit room name (auto-generated if not provided)
            metadata: Additional call metadata
            play_ringtone: Whether to play ringtone while connecting
            hide_phone_number: Whether to hide caller ID
            
        Returns:
            Dictionary containing call details including sip_call_id and room_name
            
        Raises:
            Exception: If call creation fails
        """
        try:
            # Generate room name if not provided
            if not room_name:
                timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
                room_name = f"outbound-{to_number.replace('+', '')}-{timestamp}"
            
            logger.info(
                f"Creating outbound call: from={from_number} to={to_number} "
                f"via trunk={trunk_id} room={room_name}"
            )
            
            # Validate phone numbers
            if not self._validate_phone_number(to_number):
                raise ValueError(f"Invalid destination number: {to_number}")
            
            if not self._validate_phone_number(from_number):
                raise ValueError(f"Invalid source number: {from_number}")
            
            # Enrich metadata
            enriched_metadata = {
                "call_type": "outbound",
                "initiated_at": datetime.now().isoformat(),
                "destination": to_number,
                "caller_id": from_number,
                **(metadata or {})
            }
            
            # Create SIP participant (outbound call)
            result = await self.lk_api.sip.create_sip_participant(
                api.CreateSIPParticipantRequest(
                    sip_trunk_id=trunk_id,
                    sip_call_to=to_number,
                    room_name=room_name,
                    participant_identity=f"sip-outbound-{to_number}",
                    participant_name=f"Outbound to {to_number}",
                    participant_metadata=str(enriched_metadata),
                    dtmf="",
                    play_ringtone=play_ringtone,
                    hide_phone_number=hide_phone_number
                )
            )
            
            # Close the aiohttp session properly
            if hasattr(self.lk_api, 'aclose'):
                await self.lk_api.aclose()
            
            call_info = {
                "sip_call_id": result.sip_call_id,
                "participant_id": result.participant_id,
                "participant_identity": result.participant_identity,
                "room_name": room_name,
                "to_number": to_number,
                "from_number": from_number,
                "trunk_id": trunk_id,
                "status": "initiating",
                "metadata": enriched_metadata
            }
            
            logger.info(
                f"Outbound call created: sip_call_id={result.sip_call_id} "
                f"participant_id={result.participant_id} room={room_name}"
            )
            
            # Store in database if available
            if self.db_pool:
                await self._store_outbound_call(call_info)
            
            return call_info
            
        except ValueError as e:
            logger.error(f"Validation error creating outbound call: {e}")
            raise
        except Exception as e:
            logger.error(
                f"Failed to create outbound call to {to_number}: {e}",
                exc_info=True
            )
            raise
    
    async def create_callback_call(
        self,
        customer_phone: str,
        from_number: str,
        trunk_id: str,
        customer_id: Optional[int] = None,
        reason: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> Dict:
        """
        Initiate a callback to a customer
        
        Args:
            customer_phone: Customer's phone number
            from_number: Company phone number for caller ID
            trunk_id: Outbound SIP trunk ID
            customer_id: Customer database ID (optional)
            reason: Reason for callback
            metadata: Additional metadata
            
        Returns:
            Call information dictionary
        """
        callback_metadata = {
            "call_purpose": "callback",
            "customer_id": customer_id,
            "callback_reason": reason or "scheduled_callback",
            **(metadata or {})
        }
        
        room_name = f"callback-{customer_phone.replace('+', '')}-{int(datetime.now().timestamp())}"
        
        logger.info(f"Initiating callback to customer {customer_phone}: {reason}")
        
        return await self.create_outbound_call(
            to_number=customer_phone,
            from_number=from_number,
            trunk_id=trunk_id,
            room_name=room_name,
            metadata=callback_metadata,
            play_ringtone=True
        )
    
    async def create_notification_call(
        self,
        to_number: str,
        from_number: str,
        trunk_id: str,
        notification_type: str,
        message: str,
        metadata: Optional[Dict] = None
    ) -> Dict:
        """
        Create an automated notification call
        
        Args:
            to_number: Destination phone number
            from_number: Source phone number
            trunk_id: Outbound trunk ID
            notification_type: Type of notification (e.g., 'appointment_reminder', 'payment_due')
            message: Message to deliver
            metadata: Additional metadata
            
        Returns:
            Call information dictionary
        """
        notification_metadata = {
            "call_purpose": "notification",
            "notification_type": notification_type,
            "message": message,
            "automated": True,
            **(metadata or {})
        }
        
        room_name = f"notify-{notification_type}-{to_number.replace('+', '')}-{int(datetime.now().timestamp())}"
        
        logger.info(
            f"Creating notification call to {to_number}: "
            f"type={notification_type}"
        )
        
        return await self.create_outbound_call(
            to_number=to_number,
            from_number=from_number,
            trunk_id=trunk_id,
            room_name=room_name,
            metadata=notification_metadata,
            play_ringtone=False
        )
    
    async def transfer_to_external_number(
        self,
        room_name: str,
        to_number: str,
        from_number: str,
        trunk_id: str,
        transfer_type: str = "cold",
        metadata: Optional[Dict] = None
    ) -> Dict:
        """
        Transfer an active call to an external number
        
        Args:
            room_name: Current LiveKit room name
            to_number: Number to transfer to
            from_number: Caller ID for transfer
            trunk_id: Outbound trunk ID
            transfer_type: 'cold' or 'warm' transfer
            metadata: Additional metadata
            
        Returns:
            Transfer result dictionary
        """
        try:
            transfer_metadata = {
                "call_purpose": "transfer",
                "transfer_type": transfer_type,
                "original_room": room_name,
                "transfer_to": to_number,
                **(metadata or {})
            }
            
            logger.info(
                f"Transferring call from room {room_name} to {to_number} "
                f"(type: {transfer_type})"
            )
            
            # Create new SIP participant for transfer destination
            result = await self.lk_api.sip.create_sip_participant(
                api.CreateSIPParticipantRequest(
                    sip_trunk_id=trunk_id,
                    sip_call_to=to_number,
                    room_name=room_name,  # Same room for warm transfer
                    participant_identity=f"transfer-{to_number}",
                    participant_name=f"Transfer to {to_number}",
                    participant_metadata=str(transfer_metadata),
                    play_ringtone=True
                )
            )
            
            transfer_info = {
                "success": True,
                "sip_call_id": result.sip_call_id,
                "participant_id": result.participant_id,
                "room_name": room_name,
                "transfer_type": transfer_type,
                "to_number": to_number,
                "message": f"Call transferred to {to_number}"
            }
            
            logger.info(
                f"Transfer successful: sip_call_id={result.sip_call_id}"
            )
            
            return transfer_info
            
        except Exception as e:
            logger.error(
                f"Failed to transfer call to {to_number}: {e}",
                exc_info=True
            )
            return {
                "success": False,
                "error": str(e),
                "message": "Transfer failed"
            }
    
    async def batch_create_calls(
        self,
        call_list: List[Dict],
        trunk_id: str,
        from_number: str,
        delay_seconds: int = 2
    ) -> List[Dict]:
        """
        Create multiple outbound calls in batch with delay between calls
        
        Args:
            call_list: List of call dictionaries with 'to_number' and optional 'metadata'
            trunk_id: Outbound trunk ID to use
            from_number: Caller ID number
            delay_seconds: Delay between calls to avoid rate limiting
            
        Returns:
            List of call results
        """
        results = []
        
        logger.info(
            f"Starting batch call creation: {len(call_list)} calls "
            f"with {delay_seconds}s delay"
        )
        
        for idx, call_info in enumerate(call_list, 1):
            try:
                to_number = call_info.get("to_number")
                metadata = call_info.get("metadata", {})
                metadata["batch_index"] = idx
                metadata["batch_total"] = len(call_list)
                
                result = await self.create_outbound_call(
                    to_number=to_number,
                    from_number=from_number,
                    trunk_id=trunk_id,
                    metadata=metadata
                )
                
                results.append({
                    "success": True,
                    "call_info": result,
                    "index": idx
                })
                
                logger.info(f"Batch call {idx}/{len(call_list)} created successfully")
                
                # Delay before next call
                if idx < len(call_list):
                    await asyncio.sleep(delay_seconds)
                    
            except Exception as e:
                logger.error(f"Batch call {idx} failed: {e}")
                results.append({
                    "success": False,
                    "error": str(e),
                    "to_number": call_info.get("to_number"),
                    "index": idx
                })
        
        success_count = sum(1 for r in results if r.get("success"))
        logger.info(
            f"Batch call creation completed: {success_count}/{len(call_list)} successful"
        )
        
        return results
    
    # ==================== DATABASE OPERATIONS ====================
    
    async def _store_outbound_call(self, call_info: Dict) -> Optional[int]:
        """
        Store outbound call information in database
        
        Args:
            call_info: Call information dictionary
            
        Returns:
            Database record ID or None
        """
        if not self.db_pool:
            logger.debug("No database pool available, skipping storage")
            return None
        
        try:
            async with self.db_pool.acquire() as conn:
                # Convert metadata dict to JSON string for PostgreSQL
                import json
                metadata = call_info.get("metadata", {})
                metadata_json = json.dumps(metadata) if isinstance(metadata, dict) else metadata
                
                record_id = await conn.fetchval(
                    """
                    INSERT INTO outbound_calls 
                    (sip_call_id, participant_id, room_name, to_number, 
                     from_number, trunk_id, status, metadata, created_at)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8::jsonb, $9)
                    RETURNING id
                    """,
                    call_info.get("sip_call_id"),
                    call_info.get("participant_id"),
                    call_info.get("room_name"),
                    call_info.get("to_number"),
                    call_info.get("from_number"),
                    call_info.get("trunk_id"),
                    call_info.get("status", "initiating"),
                    metadata_json,
                    datetime.now()
                )
                
                logger.debug(f"Stored outbound call in database: id={record_id}")
                return record_id
                
        except Exception as e:
            logger.error(f"Failed to store outbound call in database: {e}")
            return None
    
    async def update_call_status(
        self,
        sip_call_id: str,
        status: str,
        additional_data: Optional[Dict] = None
    ) -> bool:
        """
        Update outbound call status in database
        
        Args:
            sip_call_id: SIP call ID
            status: New status (e.g., 'ringing', 'answered', 'completed', 'failed')
            additional_data: Additional data to store
            
        Returns:
            True if update successful
        """
        if not self.db_pool:
            logger.debug("No database pool available, skipping update")
            return False
        
        try:
            async with self.db_pool.acquire() as conn:
                await conn.execute(
                    """
                    UPDATE outbound_calls
                    SET status = $1,
                        updated_at = $2,
                        metadata = metadata || $3::jsonb
                    WHERE sip_call_id = $4
                    """,
                    status,
                    datetime.now(),
                    additional_data or {},
                    sip_call_id
                )
                
                logger.debug(f"Updated call status: sip_call_id={sip_call_id} status={status}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to update call status: {e}")
            return False
    
    # ==================== UTILITY METHODS ====================
    
    def _validate_phone_number(self, phone_number: str) -> bool:
        """
        Basic phone number validation
        
        Args:
            phone_number: Phone number to validate
            
        Returns:
            True if valid format
        """
        if not phone_number:
            return False
        
        # Remove common formatting characters
        clean_number = phone_number.replace("+", "").replace("-", "").replace(" ", "").replace("(", "").replace(")", "")
        
        # Check if it's all digits and reasonable length
        if not clean_number.isdigit():
            return False
        
        # Check length (typically 10-15 digits for international numbers)
        if len(clean_number) < 10 or len(clean_number) > 15:
            return False
        
        return True
    
    async def get_active_outbound_calls(self) -> List[Dict]:
        """
        Get all active outbound calls
        
        Returns:
            List of active call dictionaries
        """
        if not self.db_pool:
            logger.warning("No database pool available")
            return []
        
        try:
            async with self.db_pool.acquire() as conn:
                calls = await conn.fetch(
                    """
                    SELECT sip_call_id, participant_id, room_name, to_number,
                           from_number, trunk_id, status, metadata, created_at
                    FROM outbound_calls
                    WHERE status IN ('initiating', 'ringing', 'answered')
                    ORDER BY created_at DESC
                    """
                )
                
                return [dict(call) for call in calls]
                
        except Exception as e:
            logger.error(f"Failed to get active outbound calls: {e}")
            return []