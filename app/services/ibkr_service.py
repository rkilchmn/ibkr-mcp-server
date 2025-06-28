import os
from typing import List, Dict
from fastapi import HTTPException
from ib_async import IB
from dotenv import load_dotenv
import asyncio
import nest_asyncio
try:
    nest_asyncio.apply()
except ValueError as e:
    print(f"nest_asyncio.apply() skipped: {e}")

# import logging
# logging.basicConfig(level=logging.DEBUG)

load_dotenv(override=True)

class IBKRService:
    def __init__(self):
        self.ib = IB()
        self.host = os.getenv("IBKR_HOST", "127.0.0.1")
        raw_port = os.getenv("IBKR_PORT", "7496").split()[0]
        self.port = int(raw_port)
        self.connected = False
        
    async def connect(self):
        """Connect to IBKR TWS or Gateway"""
        if self.connected:
            return
            
        try:
            print(f"Connecting to IBKR at {self.host}:{self.port}")
            await self.ib.connectAsync(
                host=self.host,
                port=self.port,
                clientId=0,
                readonly=True,
                timeout=20
            )
            self.connected = True
            print(f"Connected to IBKR at {self.host}:{self.port}")
        except Exception as e:
            self.connected = False
            raise HTTPException(status_code=500, detail=f"Failed to connect to IBKR: {str(e)}")

    def disconnect(self):
        """Disconnect from IBKR"""
        if self.connected:
            self.ib.disconnect()
            self.connected = False
            print("Disconnected from IBKR")

    async def fetch_portfolio_details(self) -> Dict:
        """Fetch portfolio details from IBKR"""
        try:
            if not self.connected:
                await self.connect()
            
            print("=>>>>>> Fetching portfolio details")
            # Get portfolio positions
            positions = await asyncio.to_thread(self.ib.positions)
            print("=>>>>>> Positions fetched: ", positions)
            
            # Format portfolio data
            portfolio_data = []
            for pos in positions:
                position_data = {
                    'symbol': pos.contract.symbol,
                    'secType': pos.contract.secType,
                    'exchange': pos.contract.exchange,
                    'currency': pos.contract.currency,
                    'position': pos.position,
                    'avgCost': pos.avgCost
                }
                portfolio_data.append(position_data)
            
            print("=>>>>>> Portfolio data: ", portfolio_data)
            # Get account summary
            print("=>>>>>> Fetching account summary")
            account = await self.ib.accountSummaryAsync()
            
            return {
                'positions': portfolio_data,
                'account_summary': account
            }
            
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to fetch portfolio: {str(e)}"
            )
        finally:
            self.disconnect()

# Create a singleton instance
ibkr_service = IBKRService()