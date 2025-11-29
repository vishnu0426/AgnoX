"""
SIP Trunk Manager for LiveKit Cloud
Handles both inbound and outbound SIP trunk operations
Production-ready implementation
"""

import logging
from typing import Dict, Optional, List
from livekit import api
from config.livekit_config import livekit_config

logger = logging.getLogger(__name__)


class SIPTrunkManager:
    """
    Comprehensive SIP trunk management for inbound and outbound calls
    Supports LiveKit Cloud telephone integration
    """
    
    def __init__(self):
        """Initialize SIP trunk manager with LiveKit API client"""
        self.lk_api = livekit_config.get_api_client()
        logger.info("SIPTrunkManager initialized")
    
    # ==================== INBOUND TRUNK OPERATIONS ====================
    
    async def create_inbound_trunk(
        self,
        name: str,
        phone_numbers: List[str],
        allowed_addresses: Optional[List[str]] = None,
        allowed_numbers: Optional[List[str]] = None,
        auth_username: Optional[str] = None,
        auth_password: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> Dict:
        """
        Create SIP inbound trunk for receiving calls
        
        Args:
            name: Human-readable trunk name
            phone_numbers: List of phone numbers to associate (E.164 format)
            allowed_addresses: List of allowed source IP addresses/CIDR
            allowed_numbers: List of allowed caller numbers
            auth_username: SIP authentication username (optional)
            auth_password: SIP authentication password (optional)
            metadata: Additional metadata dictionary
            
        Returns:
            Dictionary containing trunk details including trunk_id
            
        Raises:
            Exception: If trunk creation fails
        """
        try:
            logger.info(f"Creating inbound SIP trunk: {name} with {len(phone_numbers)} number(s)")
            
            trunk_info = api.SIPInboundTrunkInfo(
                name=name,
                numbers=phone_numbers,
                metadata=str(metadata or {})
            )
            
            # Add authentication if provided
            if auth_username and auth_password:
                trunk_info.auth_username = auth_username
                trunk_info.auth_password = auth_password
                logger.debug(f"Authentication configured for trunk: {name}")
            
            # Add allowed addresses if provided
            if allowed_addresses:
                trunk_info.allowed_addresses = allowed_addresses
                logger.debug(f"Allowed addresses configured: {len(allowed_addresses)}")
            
            # Add allowed numbers if provided
            if allowed_numbers:
                trunk_info.allowed_numbers = allowed_numbers
                logger.debug(f"Allowed numbers configured: {len(allowed_numbers)}")
            
            trunk = await self.lk_api.sip.create_sip_inbound_trunk(
                api.CreateSIPInboundTrunkRequest(trunk=trunk_info)
            )
            
            result = {
                "trunk_id": trunk.sip_trunk_id,
                "trunk_type": "inbound",
                "name": name,
                "numbers": phone_numbers,
                "allowed_addresses": allowed_addresses or [],
                "allowed_numbers": allowed_numbers or [],
                "has_authentication": bool(auth_username),
                "metadata": metadata or {}
            }
            
            logger.info(f"Inbound trunk created successfully: ID={trunk.sip_trunk_id}, Name={name}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to create inbound SIP trunk '{name}': {e}", exc_info=True)
            raise
    
    # ==================== OUTBOUND TRUNK OPERATIONS ====================
    
    async def create_outbound_trunk(
        self,
        name: str,
        address: str,
        transport: str = "sip_transport_auto",
        phone_numbers: Optional[List[str]] = None,
        auth_username: Optional[str] = None,
        auth_password: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None,
        metadata: Optional[Dict] = None
    ) -> Dict:
        """
        Create SIP outbound trunk for making calls
        
        Args:
            name: Human-readable trunk name
            address: SIP server address (e.g., sip.provider.com or IP:port)
            transport: Transport protocol ("sip_transport_auto", "sip_transport_udp", "sip_transport_tcp", "sip_transport_tls")
            phone_numbers: List of phone numbers for outbound calls (E.164 format)
            auth_username: SIP authentication username
            auth_password: SIP authentication password
            headers: Custom SIP headers to include
            metadata: Additional metadata dictionary
            
        Returns:
            Dictionary containing trunk details including trunk_id
            
        Raises:
            Exception: If trunk creation fails
        """
        try:
            logger.info(f"Creating outbound SIP trunk: {name} to {address}")
            
            trunk_info = api.SIPOutboundTrunkInfo(
                name=name,
                address=address,
                transport=transport,
                numbers=phone_numbers or [],
                metadata=str(metadata or {})
            )
            
            # Add authentication if provided
            if auth_username and auth_password:
                trunk_info.auth_username = auth_username
                trunk_info.auth_password = auth_password
                logger.debug(f"Authentication configured for outbound trunk: {name}")
            
            # Add custom headers if provided
            if headers:
                trunk_info.headers = headers
                logger.debug(f"Custom headers configured: {len(headers)}")
            
            trunk = await self.lk_api.sip.create_sip_outbound_trunk(
                api.CreateSIPOutboundTrunkRequest(trunk=trunk_info)
            )
            
            result = {
                "trunk_id": trunk.sip_trunk_id,
                "trunk_type": "outbound",
                "name": name,
                "address": address,
                "transport": transport,
                "numbers": phone_numbers or [],
                "has_authentication": bool(auth_username),
                "headers": headers or {},
                "metadata": metadata or {}
            }
            
            logger.info(f"Outbound trunk created successfully: ID={trunk.sip_trunk_id}, Name={name}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to create outbound SIP trunk '{name}': {e}", exc_info=True)
            raise
    
    # ==================== TRUNK LISTING OPERATIONS ====================
    
    async def list_inbound_trunks(self) -> List[Dict]:
        """
        List all inbound SIP trunks
        
        Returns:
            List of inbound trunk dictionaries
        """
        try:
            logger.debug("Fetching inbound SIP trunks")
            
            response = await self.lk_api.sip.list_sip_inbound_trunk(
                api.ListSIPInboundTrunkRequest()
            )
            
            trunks = []
            for trunk in response:
                trunk_dict = {
                    "trunk_id": trunk.sip_trunk_id,
                    "trunk_type": "inbound",
                    "name": trunk.name,
                    "numbers": list(trunk.numbers) if trunk.numbers else [],
                    "allowed_addresses": list(trunk.allowed_addresses) if hasattr(trunk, 'allowed_addresses') and trunk.allowed_addresses else [],
                    "allowed_numbers": list(trunk.allowed_numbers) if hasattr(trunk, 'allowed_numbers') and trunk.allowed_numbers else [],
                    "metadata": trunk.metadata if trunk.metadata else "{}"
                }
                trunks.append(trunk_dict)
            
            logger.info(f"Retrieved {len(trunks)} inbound trunk(s)")
            return trunks
            
        except Exception as e:
            logger.error(f"Failed to list inbound SIP trunks: {e}", exc_info=True)
            return []
    
    async def list_outbound_trunks(self) -> List[Dict]:
        """
        List all outbound SIP trunks
        
        Returns:
            List of outbound trunk dictionaries
        """
        try:
            logger.debug("Fetching outbound SIP trunks")
            
            response = await self.lk_api.sip.list_sip_outbound_trunk(
                api.ListSIPOutboundTrunkRequest()
            )
            
            trunks = []
            for trunk in response:
                trunk_dict = {
                    "trunk_id": trunk.sip_trunk_id,
                    "trunk_type": "outbound",
                    "name": trunk.name,
                    "address": trunk.address if hasattr(trunk, 'address') else None,
                    "transport": trunk.transport if hasattr(trunk, 'transport') else None,
                    "numbers": list(trunk.numbers) if trunk.numbers else [],
                    "metadata": trunk.metadata if trunk.metadata else "{}"
                }
                trunks.append(trunk_dict)
            
            logger.info(f"Retrieved {len(trunks)} outbound trunk(s)")
            return trunks
            
        except Exception as e:
            logger.error(f"Failed to list outbound SIP trunks: {e}", exc_info=True)
            return []
    
    async def list_all_trunks(self) -> Dict[str, List[Dict]]:
        """
        List all SIP trunks (both inbound and outbound)
        
        Returns:
            Dictionary with 'inbound' and 'outbound' keys containing trunk lists
        """
        try:
            inbound_trunks = await self.list_inbound_trunks()
            outbound_trunks = await self.list_outbound_trunks()
            
            result = {
                "inbound": inbound_trunks,
                "outbound": outbound_trunks,
                "total_inbound": len(inbound_trunks),
                "total_outbound": len(outbound_trunks)
            }
            
            logger.info(
                f"Retrieved all trunks: {len(inbound_trunks)} inbound, "
                f"{len(outbound_trunks)} outbound"
            )
            return result
            
        except Exception as e:
            logger.error(f"Failed to list all SIP trunks: {e}", exc_info=True)
            return {"inbound": [], "outbound": [], "total_inbound": 0, "total_outbound": 0}
    
    # ==================== TRUNK DELETION OPERATIONS ====================
    
    async def delete_trunk(self, trunk_id: str) -> bool:
        """
        Delete a SIP trunk (inbound or outbound)
        
        Args:
            trunk_id: Trunk ID to delete
            
        Returns:
            True if deletion successful, False otherwise
        """
        try:
            logger.info(f"Deleting SIP trunk: {trunk_id}")
            
            await self.lk_api.sip.delete_sip_trunk(
                api.DeleteSIPTrunkRequest(sip_trunk_id=trunk_id)
            )
            
            logger.info(f"SIP trunk deleted successfully: {trunk_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete SIP trunk {trunk_id}: {e}", exc_info=True)
            return False
    
    # ==================== TRUNK VALIDATION OPERATIONS ====================
    
    async def validate_trunk_exists(self, trunk_id: str) -> bool:
        """
        Check if a trunk exists in the system
        
        Args:
            trunk_id: Trunk ID to validate
            
        Returns:
            True if trunk exists, False otherwise
        """
        try:
            all_trunks = await self.list_all_trunks()
            
            # Check inbound trunks
            for trunk in all_trunks["inbound"]:
                if trunk["trunk_id"] == trunk_id:
                    logger.debug(f"Trunk validated (inbound): {trunk_id}")
                    return True
            
            # Check outbound trunks
            for trunk in all_trunks["outbound"]:
                if trunk["trunk_id"] == trunk_id:
                    logger.debug(f"Trunk validated (outbound): {trunk_id}")
                    return True
            
            logger.warning(f"Trunk not found: {trunk_id}")
            return False
            
        except Exception as e:
            logger.error(f"Error validating trunk {trunk_id}: {e}", exc_info=True)
            return False
    
    async def get_trunk_by_id(self, trunk_id: str) -> Optional[Dict]:
        """
        Get trunk details by ID
        
        Args:
            trunk_id: Trunk ID to retrieve
            
        Returns:
            Trunk dictionary or None if not found
        """
        try:
            all_trunks = await self.list_all_trunks()
            
            # Search inbound trunks
            for trunk in all_trunks["inbound"]:
                if trunk["trunk_id"] == trunk_id:
                    logger.debug(f"Found trunk (inbound): {trunk_id}")
                    return trunk
            
            # Search outbound trunks
            for trunk in all_trunks["outbound"]:
                if trunk["trunk_id"] == trunk_id:
                    logger.debug(f"Found trunk (outbound): {trunk_id}")
                    return trunk
            
            logger.warning(f"Trunk not found: {trunk_id}")
            return None
            
        except Exception as e:
            logger.error(f"Error getting trunk {trunk_id}: {e}", exc_info=True)
            return None
    
    # ==================== UTILITY OPERATIONS ====================
    
    async def get_trunk_statistics(self, trunk_id: str) -> Dict:
        """
        Get statistics for a specific trunk
        Note: This requires integration with call tracking system
        
        Args:
            trunk_id: Trunk ID
            
        Returns:
            Statistics dictionary
        """
        trunk = await self.get_trunk_by_id(trunk_id)
        
        if not trunk:
            logger.warning(f"Cannot get statistics for non-existent trunk: {trunk_id}")
            return {
                "trunk_id": trunk_id,
                "exists": False,
                "error": "Trunk not found"
            }
        
        # Placeholder for actual call statistics
        # This would integrate with your call_sessions table
        return {
            "trunk_id": trunk_id,
            "trunk_type": trunk.get("trunk_type"),
            "trunk_name": trunk.get("name"),
            "exists": True,
            "total_calls": 0,  # Would query from database
            "active_calls": 0,
            "failed_calls": 0,
            "last_call_time": None
        }