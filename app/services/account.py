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
                        currency=item.currency,
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
                    currency=item.currency,
                )
                for item in account_values
            ]
        except Exception as e:
            logger.error(f"Failed to get account values: {e}")
            raise Exception(f"Account values error: {e}")

    async def get_positions_detailed(self) -> list[Position]:
        """Get all positions with detailed information.

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
