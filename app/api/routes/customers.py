import logging
from fastapi import APIRouter, Depends, HTTPException, status, Query
import asyncpg

from app.api.dependencies import get_db_pool, verify_token
from app.api.schemas.customer_schema import (
    CustomerResponse,
    CustomerHistoryResponse,
    CallHistoryEntry
)
from app.services.customer_service import CustomerService

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/customers/{phone_number}", response_model=CustomerResponse)
async def get_customer(
    phone_number: str,
    db_pool: asyncpg.Pool = Depends(get_db_pool),
    token: str = Depends(verify_token)
):
    """Get customer information"""
    try:
        customer_service = CustomerService(db_pool)
        customer = await customer_service.get_customer_info(phone_number)
        
        if not customer:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Customer not found"
            )
        
        return CustomerResponse(**customer)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get customer: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve customer"
        )


@router.get("/customers/{customer_id}/history", response_model=CustomerHistoryResponse)
async def get_customer_history(
    customer_id: int,
    limit: int = Query(default=10, ge=1, le=100),
    db_pool: asyncpg.Pool = Depends(get_db_pool),
    token: str = Depends(verify_token)
):
    """Get customer call history"""
    try:
        customer_service = CustomerService(db_pool)
        
        async with db_pool.acquire() as conn:
            customer = await conn.fetchrow(
                """
                SELECT customer_id, phone_number, name, email,
                       created_at, 0 as total_calls, NULL as last_call_time
                FROM customers
                WHERE customer_id = $1
                """,
                customer_id
            )
            
            if not customer:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Customer not found"
                )
        
        history = await customer_service.get_call_history(customer_id, limit)
        
        return CustomerHistoryResponse(
            customer=CustomerResponse(**dict(customer)),
            history=[CallHistoryEntry(**h) for h in history]
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get customer history: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve customer history"
        )
