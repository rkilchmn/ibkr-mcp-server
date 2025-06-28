import asyncio
from ibkr_service import ibkr_service

import nest_asyncio
nest_asyncio.apply()

async def test_portfolio():
    try:
        ibkr_service.connect()
        portfolio = ibkr_service.fetch_portfolio_details()
        print("Portfolio:", portfolio)
    except Exception as e:
        print("Portfolio fetch failed:", e)

if __name__ == "__main__":
    asyncio.run(test_portfolio())