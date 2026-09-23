"""Account management service."""
import asyncio
from app.services.client import IBClient
from app.core.setup_logging import logger
from app.models import AccountSummary, AccountValue, Position


class AccountClient(IBClient):
  """Account management operations."""

  def __init__(self) -> None:
    """Initialize the AccountClient."""
    super().__init__()
    self._account_lock = asyncio.Lock()

  async def get_account_summary(self, tags: str = "All") -> list[AccountSummary]:
    """Get account summary information.
    
    Args:
      tags: Tags to retrieve (default: "All")
      
    Returns:
      List of account summary items
    """
    async with self._account_lock:
      await self._connect()
      
      try:
        # Always unsubscribe from any existing subscription first
        self.ib.reqAccountUpdates(False)
        await asyncio.sleep(0.1)
        
        summary_items = self.ib.accountSummary()
        
        if not summary_items:
          self.ib.reqAccountUpdates(True)
          await asyncio.sleep(2)
          summary_items = self.ib.accountSummary()
      
        return [
          AccountSummary(
            account=item.account,
            tag=item.tag,
            value=item.value,
            currency=item.currency
          )
          for item in summary_items
        ]
      except Exception as e:
        logger.error(f"Failed to get account summary: {e}")
        raise
      finally:
        # Always unsubscribe to prevent hitting rate limits
        try:
          self.ib.reqAccountUpdates(False)
        except Exception:
          pass

  async def get_account_values(self) -> list[AccountValue]:
    """Get account values.
    
    Returns:
      List of account values
    """
    await self._connect()
    
    try:
      account_values = self.ib.accountValues()
      return [
        AccountValue(
          account=item.account,
          key=item.tag,
          value=item.value,
          currency=item.currency
        )
        for item in account_values
      ]
    except Exception as e:
      logger.error(f"Failed to get account values: {e}")
      raise Exception(f"Account values error: {e}")

  async def get_positions_detailed(self) -> list[Position]:
    """Get all positions with detailed information.
    
    Returns:
      List of positions
    """
    await self._connect()
    
    try:
      positions = await asyncio.wait_for(
          self.ib.reqPositionsAsync(),
          timeout=self.config.ib_request_timeout,
        )
      result = []
      
      for pos in positions:
        # Get market price if available
        market_price = None
        market_value = None
        unrealized_pnl = None
        
        try:
          # Request market data for the position
          ticker = self.ib.reqMktData(pos.contract, '', True, False)
          await asyncio.sleep(0.5)
          
          if ticker and ticker.last and str(ticker.last).lower() not in ['nan', 'inf', '-inf']:
            market_price = float(ticker.last)
            market_value = market_price * pos.position
            unrealized_pnl = market_value - (pos.avgCost * pos.position)
        except Exception as ticker_error:
          logger.debug(f"Could not get market data for {pos.contract.symbol}: {ticker_error}")
        
        position = Position(
          account=pos.account,
          symbol=pos.contract.symbol,
          sec_type=pos.contract.secType,
          exchange=pos.contract.exchange,
          currency=pos.contract.currency,
          position=float(pos.position),
          avg_cost=float(pos.avgCost),
          market_price=market_price,
          market_value=market_value,
          unrealized_pnl=unrealized_pnl,
          realized_pnl=None,  # Not available in position data
          contract_id=pos.contract.conId if hasattr(pos.contract, 'conId') else None
        )
        result.append(position)
      
      return result
    except Exception as e:
      logger.error(f"Failed to get positions: {e}")
      raise Exception(f"Positions error: {e}")
