from fastapi import APIRouter, HTTPException
from app.services.ibkr_service import ibkr_service

router = APIRouter()

@router.get("/portfolio")
async def get_portfolio():
    try:
        portfolio = await ibkr_service.fetch_portfolio_details()
        return portfolio
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))