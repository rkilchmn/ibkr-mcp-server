"""Position operations."""

import asyncio

from .client import IBClient
from app.core.setup_logging import logger
from app.models import Position


class PositionClient(IBClient):
    """Position operations.

    Available public methods:
      - get_positions: get account positions with detailed information

    """

    async def get_positions(self) -> list[Position]:
        """Get account positions with detailed information.

        Returns:
          List of positions with market data and P&L from PortfolioItem.
        """
        await self._connect()

        try:
            # Get managed accounts to determine which account(s) to subscribe to
            accounts = self.ib.managedAccounts()
            result = []

            for account in accounts:
                # Subscribe to account and portfolio updates
                try:
                    await asyncio.wait_for(
                        self.ib.reqAccountUpdatesAsync(account),
                        timeout=self.config.ib_request_timeout,
                    )
                except (asyncio.TimeoutError, Exception) as e:
                    logger.warning(f"Account updates timeout for {account}: {e}")

                # Get portfolio items for this account
                for item in self.ib.portfolio(account):
                    # Calculate normalized avg_cost (per share) using contract multiplier
                    try:
                        multiplier = float(item.contract.multiplier or 1)
                        avg_cost = float(item.averageCost) / multiplier
                    except (ValueError, TypeError, AttributeError):
                        logger.warning(
                            f"Invalid multiplier {item.contract.localSymbol}, using 1"
                        )
                        avg_cost = float(item.averageCost)

                    position = Position(
                        account=item.account,
                        symbol=item.contract.symbol,
                        sec_type=item.contract.secType,
                        exchange=item.contract.exchange,
                        currency=item.contract.currency,
                        position=float(item.position),
                        avg_cost=avg_cost,
                        market_price=float(item.marketPrice)
                        if item.marketPrice
                        else None,
                        market_value=float(item.marketValue)
                        if item.marketValue
                        else None,
                        unrealized_pnl=float(item.unrealizedPNL)
                        if item.unrealizedPNL
                        else None,
                        realized_pnl=float(item.realizedPNL)
                        if item.realizedPNL
                        else None,
                        contract_id=item.contract.conId
                        if hasattr(item.contract, "conId")
                        else None,
                        local_symbol=item.contract.localSymbol,
                    )
                    result.append(position)

                # Unsubscribe from account updates
                self.ib.client.reqAccountUpdates(False, account)

            return result
        except Exception as e:
            logger.error(f"Failed to get positions: {e}")
            raise Exception(f"Positions error: {e}")
