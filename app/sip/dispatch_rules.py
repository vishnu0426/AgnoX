import logging
import json
from typing import Dict, Optional, List
from datetime import datetime
from livekit import api
from config.livekit_config import livekit_config

logger = logging.getLogger(__name__)


class SIPDispatchManager:
    """
    Manage SIP dispatch rules for intelligent call routing
    Routes incoming calls to appropriate rooms based on rules
    """
    
    def __init__(self):
        """Initialize dispatch manager with LiveKit API client"""
        self.lk_api = livekit_config.get_api_client()
        logger.info("SIPDispatchManager initialized")
    
    async def create_dispatch_rule(
        self,
        name: str,
        trunk_ids: List[str],
        room_name_pattern: str = "call-{call_id}",
        metadata: Optional[Dict] = None,
        pin: str = "",
        hide_phone_number: bool = False
    ) -> Dict:
        """
        Create SIP dispatch rule for routing incoming calls
        
        Args:
            name: Human-readable rule name
            trunk_ids: List of SIP trunk IDs to apply this rule to
            room_name_pattern: Pattern for generating room names
                             Supports: {call_id}, {phone_number}, {trunk_id}
            metadata: Additional metadata to attach to calls
            pin: Optional PIN for call authentication
            hide_phone_number: Whether to hide caller's phone number
            
        Returns:
            Created rule information with rule_id
            
        Raises:
            Exception: If rule creation fails
        """
        try:
            logger.info(
                f"Creating dispatch rule '{name}' for {len(trunk_ids)} trunk(s)"
            )
            
            # Validate trunk IDs
            for trunk_id in trunk_ids:
                if not await self._validate_trunk_id(trunk_id):
                    logger.warning(f"Trunk may not exist: {trunk_id}")
            
            # Enrich metadata with creation info
            enriched_metadata = {
                "created_at": datetime.now().isoformat(),
                "rule_name": name,
                "routing_version": "v1",
                **(metadata or {})
            }
            
            rule = await self.lk_api.sip.create_sip_dispatch_rule(
                api.CreateSIPDispatchRuleRequest(
                    rule=api.SIPDispatchRuleDirect(
                        room_name=room_name_pattern,
                        pin=pin
                    ),
                    trunk_ids=trunk_ids,
                    name=name,
                    hide_phone_number=hide_phone_number,
                    metadata=json.dumps(enriched_metadata)
                )
            )
            
            result = {
                "rule_id": rule.sip_dispatch_rule_id,
                "name": name,
                "trunk_ids": trunk_ids,
                "room_pattern": room_name_pattern,
                "hide_phone_number": hide_phone_number,
                "has_pin": bool(pin),
                "metadata": enriched_metadata
            }
            
            logger.info(
                f"Dispatch rule created: ID={rule.sip_dispatch_rule_id}, "
                f"Name={name}, Pattern={room_name_pattern}"
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to create dispatch rule '{name}': {e}", exc_info=True)
            raise
    
    async def list_dispatch_rules(self) -> List[Dict]:
        """
        List all dispatch rules configured in the system
        
        Returns:
            List of dispatch rules with details
        """
        try:
            logger.debug("Fetching all dispatch rules")
            
            response = await self.lk_api.sip.list_sip_dispatch_rule(
                api.ListSIPDispatchRuleRequest()
            )
            
            rules = []
            for rule in response:
                rule_dict = {
                    "rule_id": rule.sip_dispatch_rule_id,
                    "name": rule.name,
                    "trunk_ids": list(rule.trunk_ids) if rule.trunk_ids else [],
                    "hide_phone_number": rule.hide_phone_number,
                    "metadata": {}
                }
                
                # Parse metadata safely
                if rule.metadata:
                    try:
                        rule_dict["metadata"] = json.loads(rule.metadata)
                    except json.JSONDecodeError:
                        logger.warning(f"Invalid metadata JSON for rule {rule.sip_dispatch_rule_id}")
                        rule_dict["metadata"] = {"raw": rule.metadata}
                
                # Extract room pattern if available
                if hasattr(rule, 'rule') and hasattr(rule.rule, 'room_name'):
                    rule_dict["room_pattern"] = rule.rule.room_name
                
                # Extract PIN status
                if hasattr(rule, 'rule') and hasattr(rule.rule, 'pin'):
                    rule_dict["has_pin"] = bool(rule.rule.pin)
                
                rules.append(rule_dict)
            
            logger.info(f"Retrieved {len(rules)} dispatch rule(s)")
            return rules
            
        except Exception as e:
            logger.error(f"Failed to list dispatch rules: {e}", exc_info=True)
            return []
    
    async def get_dispatch_rule(self, rule_id: str) -> Optional[Dict]:
        """
        Get details of a specific dispatch rule
        
        Args:
            rule_id: Dispatch rule ID
            
        Returns:
            Rule details or None if not found
        """
        try:
            rules = await self.list_dispatch_rules()
            for rule in rules:
                if rule["rule_id"] == rule_id:
                    logger.debug(f"Found dispatch rule: {rule_id}")
                    return rule
            
            logger.warning(f"Dispatch rule not found: {rule_id}")
            return None
            
        except Exception as e:
            logger.error(f"Error getting dispatch rule {rule_id}: {e}", exc_info=True)
            return None
    
    async def update_dispatch_rule(
        self,
        rule_id: str,
        name: Optional[str] = None,
        trunk_ids: Optional[List[str]] = None,
        room_name_pattern: Optional[str] = None,
        metadata: Optional[Dict] = None,
        pin: Optional[str] = None,
        hide_phone_number: Optional[bool] = None
    ) -> bool:
        """
        Update an existing dispatch rule
        Note: Due to LiveKit API limitations, this deletes and recreates the rule
        
        Args:
            rule_id: Rule ID to update
            name: New name for the rule
            trunk_ids: New list of trunk IDs
            room_name_pattern: New room name pattern
            metadata: Updated metadata
            pin: New PIN
            hide_phone_number: New phone number hiding setting
            
        Returns:
            True if update successful, False otherwise
        """
        try:
            logger.info(f"Updating dispatch rule: {rule_id}")
            
            # Get current rule
            current_rule = await self.get_dispatch_rule(rule_id)
            if not current_rule:
                logger.error(f"Cannot update - rule not found: {rule_id}")
                return False
            
            # Delete existing rule
            await self.delete_dispatch_rule(rule_id)
            
            # Merge metadata
            new_metadata = current_rule.get("metadata", {})
            if metadata:
                new_metadata.update(metadata)
            new_metadata["updated_at"] = datetime.now().isoformat()
            new_metadata["previous_rule_id"] = rule_id
            
            # Recreate with new values
            await self.create_dispatch_rule(
                name=name or current_rule["name"],
                trunk_ids=trunk_ids or current_rule["trunk_ids"],
                room_name_pattern=room_name_pattern or current_rule.get("room_pattern", "call-{call_id}"),
                metadata=new_metadata,
                pin=pin or "",
                hide_phone_number=hide_phone_number if hide_phone_number is not None else current_rule.get("hide_phone_number", False)
            )
            
            logger.info(f"Dispatch rule updated successfully: {rule_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update dispatch rule {rule_id}: {e}", exc_info=True)
            return False
    
    async def delete_dispatch_rule(self, rule_id: str) -> bool:
        """
        Delete a dispatch rule
        
        Args:
            rule_id: Rule ID to delete
            
        Returns:
            True if deletion successful, False otherwise
        """
        try:
            logger.info(f"Deleting dispatch rule: {rule_id}")
            
            await self.lk_api.sip.delete_sip_dispatch_rule(
                api.DeleteSIPDispatchRuleRequest(sip_dispatch_rule_id=rule_id)
            )
            
            logger.info(f"Dispatch rule deleted successfully: {rule_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete dispatch rule {rule_id}: {e}", exc_info=True)
            return False
    
    # ==================== PRESET RULE TEMPLATES ====================
    
    async def create_default_rule(
        self,
        trunk_ids: List[str],
        metadata: Optional[Dict] = None
    ) -> Dict:
        """
        Create a default dispatch rule for general customer service
        
        Args:
            trunk_ids: SIP trunk IDs to route
            metadata: Optional metadata
            
        Returns:
            Created rule information
        """
        default_metadata = {
            "purpose": "customer_service",
            "auto_created": True,
            "routing_strategy": "ai_first",
            "priority": "normal",
            **(metadata or {})
        }
        
        return await self.create_dispatch_rule(
            name="Default Customer Service Rule",
            trunk_ids=trunk_ids,
            room_name_pattern="call-{call_id}",
            metadata=default_metadata,
            hide_phone_number=False
        )
    
    async def create_vip_rule(
        self,
        trunk_ids: List[str],
        vip_numbers: List[str],
        metadata: Optional[Dict] = None
    ) -> Dict:
        """
        Create a high-priority dispatch rule for VIP customers
        
        Args:
            trunk_ids: SIP trunk IDs
            vip_numbers: List of VIP phone numbers
            metadata: Optional metadata
            
        Returns:
            Created rule information
        """
        vip_metadata = {
            "purpose": "vip_customer_service",
            "priority": "high",
            "vip_numbers": vip_numbers,
            "escalation_immediate": True,
            **(metadata or {})
        }
        
        return await self.create_dispatch_rule(
            name="VIP Customer Service Rule",
            trunk_ids=trunk_ids,
            room_name_pattern="vip-call-{call_id}",
            metadata=vip_metadata,
            hide_phone_number=False
        )
    
    async def create_department_rule(
        self,
        trunk_ids: List[str],
        department: str,
        metadata: Optional[Dict] = None
    ) -> Dict:
        """
        Create a department-specific dispatch rule
        
        Args:
            trunk_ids: SIP trunk IDs
            department: Department name (e.g., 'sales', 'support', 'billing')
            metadata: Optional metadata
            
        Returns:
            Created rule information
        """
        dept_metadata = {
            "purpose": f"{department}_routing",
            "department": department,
            "auto_created": False,
            **(metadata or {})
        }
        
        return await self.create_dispatch_rule(
            name=f"{department.title()} Department Rule",
            trunk_ids=trunk_ids,
            room_name_pattern=f"{department}-call-{{call_id}}",
            metadata=dept_metadata,
            hide_phone_number=False
        )
    
    async def create_after_hours_rule(
        self,
        trunk_ids: List[str],
        metadata: Optional[Dict] = None
    ) -> Dict:
        """
        Create an after-hours dispatch rule with voicemail functionality
        
        Args:
            trunk_ids: SIP trunk IDs
            metadata: Optional metadata
            
        Returns:
            Created rule information
        """
        after_hours_metadata = {
            "purpose": "after_hours_service",
            "voicemail_enabled": True,
            "operating_hours": False,
            "auto_callback": True,
            **(metadata or {})
        }
        
        return await self.create_dispatch_rule(
            name="After Hours Service Rule",
            trunk_ids=trunk_ids,
            room_name_pattern="after-hours-{call_id}",
            metadata=after_hours_metadata,
            hide_phone_number=False
        )
    
    # ==================== UTILITY METHODS ====================
    
    async def _validate_trunk_id(self, trunk_id: str) -> bool:
        """
        Validate that a trunk ID exists (internal helper)
        
        Args:
            trunk_id: Trunk ID to validate
            
        Returns:
            True if trunk exists, False otherwise
        """
        try:
            # This would call the trunk manager to verify
            # For now, just check if trunk_id is not empty
            return bool(trunk_id and len(trunk_id) > 0)
        except Exception as e:
            logger.error(f"Error validating trunk {trunk_id}: {e}")
            return False
    
    async def get_rules_by_trunk(self, trunk_id: str) -> List[Dict]:
        """
        Get all dispatch rules associated with a specific trunk
        
        Args:
            trunk_id: Trunk ID to search for
            
        Returns:
            List of rules using this trunk
        """
        try:
            all_rules = await self.list_dispatch_rules()
            trunk_rules = [
                rule for rule in all_rules
                if trunk_id in rule.get("trunk_ids", [])
            ]
            
            logger.info(f"Found {len(trunk_rules)} rule(s) for trunk {trunk_id}")
            return trunk_rules
            
        except Exception as e:
            logger.error(f"Error getting rules for trunk {trunk_id}: {e}", exc_info=True)
            return []
    
    async def get_rule_statistics(self, rule_id: str) -> Dict:
        """
        Get statistics for a dispatch rule
        Note: Requires integration with call tracking system
        
        Args:
            rule_id: Rule ID
            
        Returns:
            Statistics dictionary
        """
        rule = await self.get_dispatch_rule(rule_id)
        
        if not rule:
            logger.warning(f"Cannot get statistics for non-existent rule: {rule_id}")
            return {
                "rule_id": rule_id,
                "exists": False,
                "error": "Rule not found"
            }
        
        # Placeholder for actual call statistics
        # This would integrate with your call_sessions table
        return {
            "rule_id": rule_id,
            "rule_name": rule.get("name"),
            "exists": True,
            "total_calls": 0,  # Would query from database
            "active_calls": 0,
            "last_call_time": None,
            "trunk_count": len(rule.get("trunk_ids", []))
        }