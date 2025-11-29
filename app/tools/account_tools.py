import asyncpg
import logging
from typing import Dict, List, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class AccountTools:
    """Account-related tools for agents"""
    
    def __init__(self, db_pool: asyncpg.Pool):
        self.db_pool = db_pool
    
    async def get_account_balance(self, customer_id: int) -> str:
        """
        Get customer's current account balance
        
        Args:
            customer_id: Customer ID
            
        Returns:
            Formatted balance string
        """
        try:
            async with self.db_pool.acquire() as conn:
                balance = await conn.fetchval(
                    """
                    SELECT COALESCE(
                        (SELECT value FROM customer_metadata 
                         WHERE customer_id = $1 AND key = 'balance'),
                        '0.00'
                    )
                    """,
                    customer_id
                )
            
            return f"Your current account balance is ${balance}."
        except Exception as e:
            logger.error(f"Error getting balance: {e}")
            return "I'm having trouble accessing your balance right now. Please try again in a moment."
    
    async def get_recent_transactions(
        self, 
        customer_id: int, 
        limit: int = 5
    ) -> str:
        """
        Get recent account transactions
        
        Args:
            customer_id: Customer ID
            limit: Number of transactions to retrieve
            
        Returns:
            Formatted transaction list
        """
        try:
            # Mock implementation - replace with actual billing system
            transactions = [
                {"date": "2024-11-01", "description": "Payment received", "amount": 50.00},
                {"date": "2024-10-28", "description": "Service charge", "amount": -10.00},
                {"date": "2024-10-15", "description": "Monthly subscription", "amount": -29.99},
            ]
            
            result = "Your recent transactions:\n"
            for i, txn in enumerate(transactions[:limit], 1):
                sign = "+" if txn["amount"] > 0 else ""
                result += f"{i}. {txn['date']}: {txn['description']} - {sign}${abs(txn['amount']):.2f}\n"
            
            return result
        except Exception as e:
            logger.error(f"Error getting transactions: {e}")
            return "I'm unable to retrieve your transactions at this time."
    
    async def update_contact_info(
        self, 
        customer_id: int, 
        email: Optional[str] = None,
        phone: Optional[str] = None
    ) -> str:
        """
        Update customer contact information
        
        Args:
            customer_id: Customer ID
            email: New email address
            phone: New phone number
            
        Returns:
            Confirmation message
        """
        try:
            async with self.db_pool.acquire() as conn:
                updates = []
                values = []
                idx = 1
                
                if email:
                    updates.append(f"email = ${idx}")
                    values.append(email)
                    idx += 1
                
                if phone:
                    updates.append(f"phone_number = ${idx}")
                    values.append(phone)
                    idx += 1
                
                if updates:
                    values.append(customer_id)
                    query = f"""
                        UPDATE customers
                        SET {', '.join(updates)}, updated_at = CURRENT_TIMESTAMP
                        WHERE customer_id = ${idx}
                    """
                    await conn.execute(query, *values)
                    
                    return "I've updated your contact information successfully."
                else:
                    return "No contact information was provided to update."
                    
        except Exception as e:
            logger.error(f"Error updating contact info: {e}")
            return "I encountered an error updating your information. Please try again."