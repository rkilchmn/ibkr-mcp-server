from pydantic import BaseModel
from typing import List, Optional

class PortfolioItem(BaseModel):
    symbol: str
    quantity: float
    market_value: float
    cost_basis: float
    unrealized_pnl: float

class Portfolio(BaseModel):
    account_id: str
    items: List[PortfolioItem]
    total_market_value: float
    total_cost_basis: float
    total_unrealized_pnl: float