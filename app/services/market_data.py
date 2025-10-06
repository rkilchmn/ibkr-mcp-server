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
from app.models import TickerData, GreeksData, BarData, TickData

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

      # Convert filtered DataFrame to list of Pydantic models
      filtered_tickers = []
      for _, row in filtered_data.iterrows():
        ticker_data = TickerData(
          contractId=row["contractId"],
          symbol=row["symbol"],
          secType=row["secType"],
          last=row["last"] if pd.notna(row["last"]) else None,
          bid=row["bid"] if pd.notna(row["bid"]) else None,
          ask=row["ask"] if pd.notna(row["ask"]) else None,
          greeks=row["greeks"],
        )
        filtered_tickers.append(ticker_data)

      # Return as list of dictionaries
      return [ticker.dict() for ticker in filtered_tickers]

    except Exception as e:
      logger.error("Error filtering options: {}", str(e))
      raise

  async def get_historical_data(
      self,
      symbol: str,
      sec_type: str = "STK",
      exchange: str = "SMART",
      currency: str = "USD",
      duration: str = "1 D",
      bar_size: str = "1 min",
      what_to_show: str = "TRADES",
      use_rth: bool = True
    ) -> list[BarData]:
    """Get historical market data.
    
    Args:
      symbol: Symbol to get data for
      sec_type: Security type (default: STK)
      exchange: Exchange (default: SMART)
      currency: Currency (default: USD)
      duration: Duration string (e.g., '1 D', '1 W', '1 M')
      bar_size: Bar size (e.g., '1 min', '5 mins', '1 hour', '1 day')
      what_to_show: What to show (TRADES, MIDPOINT, BID, ASK)
      use_rth: Use regular trading hours only
      
    Returns:
      List of historical bar data
      
    Raises:
      Exception: If contract qualification fails or historical data cannot be retrieved
    """
    await self._connect()
    
    try:
      # Create contract
      ib_contract = Contract()
      ib_contract.symbol = symbol.upper()  # Ensure symbol is uppercase
      ib_contract.secType = sec_type.upper()  # Ensure security type is uppercase
      ib_contract.exchange = exchange.upper()  # Ensure exchange is uppercase
      ib_contract.currency = currency.upper()  # Ensure currency is uppercase
      
      logger.debug(f"Qualifying contract: {ib_contract}")
      
      # Qualify contract
      try:
        qualified_contracts = await self.ib.qualifyContractsAsync(ib_contract)
        if not qualified_contracts or not qualified_contracts[0]:
          raise ValueError(f"No contract found for {symbol} (type: {sec_type}, exchange: {exchange}, currency: {currency})")
        
        ib_contract = qualified_contracts[0]
        logger.debug(f"Qualified contract: {ib_contract}")
        
      except Exception as qual_error:
        error_msg = f"Failed to qualify contract {symbol} (type: {sec_type}, exchange: {exchange}): {str(qual_error)}"
        logger.error(error_msg)
        raise ValueError(error_msg) from qual_error
      
      try:
        # Request historical data
        logger.debug(f"Requesting historical data for {ib_contract.symbol} ({ib_contract.secType})...")
        bars = await self.ib.reqHistoricalDataAsync(
          contract=ib_contract,
          endDateTime='',
          durationStr=duration,
          barSizeSetting=bar_size,
          whatToShow=what_to_show,
          useRTH=use_rth,
          timeout=30  # 30 second timeout
        )
        
        if not bars:
          logger.warning(f"No historical data returned for {ib_contract.symbol} (type: {ib_contract.secType})")
          return []
        
        logger.debug(f"Received {len(bars)} bars of historical data for {ib_contract.symbol}")
        
        return [
          BarData(
            date=bar.date.isoformat() if hasattr(bar.date, 'isoformat') else str(bar.date),
            open=float(bar.open) if bar.open is not None else None,
            high=float(bar.high) if bar.high is not None else None,
            low=float(bar.low) if bar.low is not None else None,
            close=float(bar.close) if bar.close is not None else None,
            volume=int(bar.volume) if bar.volume is not None else 0,
            wap=float(bar.wap) if hasattr(bar, 'wap') and bar.wap is not None else None,
            count=int(bar.barCount) if hasattr(bar, 'barCount') and bar.barCount is not None else None
          )
          for bar in bars
        ]
        
      except Exception as hist_error:
        error_msg = f"Failed to get historical data for {ib_contract.symbol} (type: {ib_contract.secType}): {str(hist_error)}"
        logger.error(error_msg)
        raise Exception(error_msg) from hist_error
      
    except Exception as e:
      logger.error(f"Historical data error for {symbol}: {str(e)}", exc_info=True)
      raise Exception(f"Historical data error: {str(e)}")

  async def get_market_data_snapshot(
      self,
      symbol: str,
      sec_type: str = "STK",
      exchange: str = "SMART",
      currency: str = "USD",
      con_id: int | None = None
    ) -> TickData | None:
    """Get real-time market data snapshot.
    
    Args:
      symbol: Symbol to get data for
      sec_type: Security type (default: STK)
      exchange: Exchange (default: SMART)
      currency: Currency (default: USD)
      con_id: Contract ID (optional)
      
    Returns:
      Tick data or None if not available
    """
    await self._connect()
    
    try:
      # Create contract
      if con_id:
        ib_contract = Contract(conId=con_id)
      else:
        ib_contract = Contract()
        ib_contract.symbol = symbol
        ib_contract.secType = sec_type
        ib_contract.exchange = exchange
        ib_contract.currency = currency
      
      # Qualify contract
      qualified_contracts = await self.ib.qualifyContractsAsync(ib_contract)
      if not qualified_contracts:
        raise Exception(f"Could not qualify contract: {symbol}")
      
      ib_contract = qualified_contracts[0]
      
      # Request market data snapshot
      ticker = self.ib.reqMktData(ib_contract, '', True, False)
      
      # Wait for data to be populated
      await asyncio.sleep(0.5)
      
      # Extract data with NaN handling
      last = None
      bid = None
      ask = None
      bid_size = None
      ask_size = None
      volume = None
      
      if ticker:
        # Check last price
        if ticker.last and str(ticker.last).lower() not in ['nan', 'inf', '-inf']:
          try:
            last = float(ticker.last)
          except (ValueError, TypeError):
            pass
        
        # Check bid
        if ticker.bid and str(ticker.bid).lower() not in ['nan', 'inf', '-inf']:
          try:
            bid = float(ticker.bid)
          except (ValueError, TypeError):
            pass
        
        # Check ask
        if ticker.ask and str(ticker.ask).lower() not in ['nan', 'inf', '-inf']:
          try:
            ask = float(ticker.ask)
          except (ValueError, TypeError):
            pass
        
        # Check bid size
        if hasattr(ticker, 'bidSize') and ticker.bidSize:
          try:
            bid_size = int(ticker.bidSize)
          except (ValueError, TypeError):
            pass
        
        # Check ask size
        if hasattr(ticker, 'askSize') and ticker.askSize:
          try:
            ask_size = int(ticker.askSize)
          except (ValueError, TypeError):
            pass
        
        # Check volume
        if hasattr(ticker, 'volume') and ticker.volume:
          try:
            volume = int(ticker.volume)
          except (ValueError, TypeError):
            pass
        
        return TickData(
          symbol=symbol,
          contract_id=ib_contract.conId if hasattr(ib_contract, 'conId') else None,
          last=last,
          bid=bid,
          ask=ask,
          bid_size=bid_size,
          ask_size=ask_size,
          volume=volume
        )
      
      return None
      
    except Exception as e:
      logger.error(f"Failed to get market data: {e}")
      raise Exception(f"Market data error: {e}")
