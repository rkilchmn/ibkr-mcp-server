"""Market data operations."""
import asyncio
import pandas as pd
import exchange_calendars as ecals
import datetime as dt
from ib_async import util
from ib_async.contract import Contract

from .client import IBClient
from .contracts import ContractClient
from app.core.setup_logging import logger
from app.models import TickerData, GreeksData

class MarketDataClient(IBClient):
  """Market data operations."""

  def __init__(self) -> None:
    """Initialize the MarketDataClient."""
    super().__init__()
    self.contract_client = ContractClient()
    self.contract_client.ib = self.ib

  def _is_market_open(self) -> bool:
      """Check if the market is open."""
      nyse = ecals.get_calendar("NYSE")
      return nyse.is_trading_minute(dt.datetime.now(dt.UTC))

  def _process_tickers(self, tickers: list[dict]) -> list[TickerData]:
    """Process tickers to extract required fields."""
    result = util.df(tickers)
    result["contractId"] = result["contract"].apply(lambda x: x.conId)
    result["symbol"] = result["contract"].apply(lambda x: x.localSymbol)
    result["secType"] = result["contract"].apply(lambda x: x.secType)
    result["last"] = result["last"].astype(float)
    result["bid"] = result["bid"].astype(float)
    result["ask"] = result["ask"].astype(float)
    result["greeks"] = result.apply(self._greek_extraction, axis=1)

    # Convert DataFrame to list of Pydantic models
    ticker_list = []
    for _, row in result.iterrows():
      ticker_data = TickerData(
        contractId=row["contractId"],
        symbol=row["symbol"],
        secType=row["secType"],
        last=row["last"] if pd.notna(row["last"]) else None,
        bid=row["bid"] if pd.notna(row["bid"]) else None,
        ask=row["ask"] if pd.notna(row["ask"]) else None,
        greeks=row["greeks"],
      )
      ticker_list.append(ticker_data)

    return ticker_list

  def _greek_extraction(self, ticker: pd.Series) -> GreeksData | None:
    """Extract greeks from a ticker.

    Only extract greeks for options contracts, use modelGreeks.
    """
    if (
      ticker.secType == "OPT" and
      hasattr(ticker, "modelGreeks") and
      ticker.modelGreeks
    ):
      return GreeksData(
        delta=ticker.modelGreeks.delta,
        gamma=ticker.modelGreeks.gamma,
        vega=ticker.modelGreeks.vega,
        theta=ticker.modelGreeks.theta,
        impliedVol=ticker.modelGreeks.impliedVol,
      )
    return None

  async def get_tickers(
      self,
      contract_ids: list[int],
    ) -> list[dict]:
    """Get tickers for a list of contract IDs.

    Args:
        contract_ids: List of contract IDs to get tickers for.

    Returns:
        List of tickers for the given contract IDs.

    """
    try:
      await self._connect()
      contracts = [Contract(conId=contract_id) for contract_id in contract_ids]
      qualified_contracts = await self.ib.qualifyContractsAsync(*contracts)

      # First attempt to get tickers
      if self._is_market_open():
        logger.debug("Market is open, requesting live market data")
        self.ib.reqMarketDataType(1)
      else:
        logger.debug("Market is closed, requesting delayed market data")
        self.ib.reqMarketDataType(2)
      tickers = await self.ib.reqTickersAsync(*qualified_contracts)

      # Process tickers
      result = self._process_tickers(tickers)

      # Check if we got any greeks data (only for options contracts)
      options_contracts = [ticker for ticker in result if ticker.secType == "OPT"]
      has_greeks = False
      if options_contracts:
        has_greeks = any(ticker.greeks for ticker in options_contracts)

      # Only restart if we have options contracts but no greeks data
      if options_contracts and not has_greeks:
        logger.warning("No greeks data for options contracts, restarting gateway...")
        await self.send_command_to_ibc("RESTART")
        await asyncio.sleep(30)
        await self._connect()

        # Second attempt
        if self._is_market_open():
          self.ib.reqMarketDataType(1)
        else:
          self.ib.reqMarketDataType(2)
        tickers = await self.ib.reqTickersAsync(*qualified_contracts)

        # Process tickers again
        result = self._process_tickers(tickers)
        # Check if we got greeks data after restart (only for options)
        options_contracts = [ticker for ticker in result if ticker.secType == "OPT"]
        has_greeks = False
        if options_contracts:
          has_greeks = any(ticker.greeks for ticker in options_contracts)
        if options_contracts and not has_greeks:
          logger.warning("Still no greeks data after gateway restart")

      result_dict = [ticker.dict() for ticker in result]

    except Exception as e:
      logger.error("Error getting tickers: {}", str(e))
      raise
    else:
      return result_dict

  async def get_and_filter_options(
      self,
      underlying_symbol: str,
      underlying_sec_type: str,
      underlying_con_id: int,
      filters: dict | None = None,
      criteria: dict | None = None,
    ) -> list[dict]:
    """Get and filter option chain based on market data criteria.

    Args:
      underlying_symbol: Symbol of the underlying contract.
      underlying_sec_type: Security type of the underlying contract.
      underlying_con_id: ConID of the underlying contract.
      filters: Dictionary of filters to apply to the options chain,
      you must specify at least one filter to reduce the number of options in the chain,
      you must specify expirations, you can specify tradingClass, strikes, and rights.
        - tradingClass: List of trading classes to filter by.
        - expirations: List of expirations to filter by.
        - strikes: List of strikes to filter by.
        - rights: List of rights to filter by.
      criteria: Dictionary of criteria to match:
        - min_delta: Minimum delta value (float)
        - max_delta: Maximum delta value (float)

    Returns:
      List of dictionaries containing filtered option details and market data

    """
    try:
      await self._connect()  # Connect once for both operations

      # Get options chain
      options_chain = await self.contract_client.get_options_chain(
        underlying_symbol,
        underlying_sec_type,
        underlying_con_id,
        filters,
      )
      options_chain_df = pd.DataFrame(options_chain)

      # Get market data for all options
      market_data = await self.get_tickers(options_chain_df["conId"].tolist())

      if not market_data:
        logger.warning("No market data available for options")
        return []

      # Convert to DataFrame for filtering
      market_data_df = pd.DataFrame(market_data)

      # Apply criteria filters
      filtered_data = market_data_df.copy()
      logger.info("Filtered data: {}", filtered_data)

      # Apply delta range if specified
      if criteria and ("min_delta" in criteria or "max_delta" in criteria):
        # Filter out rows with missing greeks data first
        filtered_data = filtered_data[
          filtered_data["greeks"].apply(
            lambda x: bool(x and x.get("delta") is not None),
          )
        ]

        # Apply delta filters
        filtered_data = filtered_data[
          filtered_data["greeks"].apply(
            lambda x: (
              ("min_delta" not in criteria or
                x["delta"] >= criteria["min_delta"]) and
              ("max_delta" not in criteria or
                x["delta"] <= criteria["max_delta"])
            ),
          )
        ]

      if filtered_data.empty:
        logger.warning("No options found matching the criteria")
        return []

      # Return the filtered data directly (already in the correct format)
      return filtered_data.to_dict(orient="records")

    except Exception as e:
      logger.error("Error filtering options: {}", str(e))
      raise
