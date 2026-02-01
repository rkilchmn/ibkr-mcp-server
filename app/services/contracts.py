"""Contract operations."""
from typing import List, Dict, Any

from ib_async import util
from ib_async.contract import Contract, Option

from app.core.setup_logging import logger
from app.util.convert_camel_to_snake_case import (
  convert_df_columns_to_snake_case,
  obj_to_dict_snake_case,
)
from .client import IBClient

class ContractClient(IBClient):
  """Contract operations.

  Available public methods:
    - get_contract_details: get contract details for a given symbol
    - get_options_chain: get options chain for a given underlying contract

  """

  async def get_contract_details(
      self,
      symbol: str,
      sec_type: str,
      exchange: str,
      primary_exchange: str | None = None,
      currency: str | None = None,
      options: dict | None = None,
    ) -> List[Dict[str, Any]]:
    """Get contract details for a given symbol.

    Args:
      symbol: Symbol to get contract details for.
      sec_type: Security type to get contract details for, supported types are:
        - STK: Stock
        - IND: Index
        - CASH: Currency
        - BOND: Bond
        - FUT: Future
        - OPT: Option
      exchange: Exchange to get contract details for, supported exchanges are:
        - CBOE: CBOE
        - NYSE: NYSE
        - ARCA: ARCA
        - BATS: BATS
        - NASDAQ: NASDAQ
      primary_exchange: Primary exchange to get contract details for.
      currency: Currency to get contract details for.
      options: Dictionary of options to get contract details for.
        - strike: Strike price to get contract details for.
        - right: Right to get contract details for.
        - lastTradeDateOrContractMonth: Last trade date or contract month.
        - tradingClass: Trading class to get contract details for.

    Returns:
        List of contract details for the given symbol.

    """
    try:
      await self._connect()

      contract_params = {
        "strike": 0,
        "right": "",
        "lastTradeDateOrContractMonth": "",
        "tradingClass": "",
        "comboLegs": [],
      }
      if options:
        contract_params.update(options)

      contract = Contract(
        conId=0,
        symbol=symbol,
        exchange=exchange or '',
        primaryExchange=primary_exchange or '',
        currency=currency or '',
        secType=sec_type,
        **contract_params,
      )

      while True:
        contracts = await self.ib.qualifyContractsAsync(contract, returnAll=True)
        if not contracts or contracts[0] is None:
          return []

        # contracts[0] is either a Contract or a list of Contracts (if ambiguous and returnAll=True)
        if isinstance(contracts[0], list):
          contract_list = contracts[0]
          filtered = [
            c
            for c in contract_list
            if c is not None
            and (exchange is None or c.exchange == exchange)
            and (primary_exchange is None or c.primaryExchange == primary_exchange)
            and (currency is None or c.currency == currency)
          ]

          # If we have exactly 1 match, re-qualify with that contract
          if len(filtered) == 1:
            contract = filtered[0]
            continue

          # Convert Contract objects to dicts with snake_case keys
          return [obj_to_dict_snake_case(c) for c in filtered]
        else:
          contracts = convert_df_columns_to_snake_case(util.df(contracts))
          contracts = contracts[[
            "con_id",
            "symbol",
            "sec_type",
            "exchange",
            "primary_exchange",
            "currency",
            "local_symbol",
            "multiplier",
          ]]
          return contracts.to_dict(orient="records")

    except Exception as e:
      logger.error("Error getting contract details: {}", str(e))
      raise

  async def get_options_chain(
    self,
    underlying_symbol: str,
    underlying_sec_type: str,
    underlying_con_id: int,
    filters: dict | None = None,
    ) -> list[str]:
    """Get options chain for a given underlying contract.

    NOTE: skipping exchange filter as conId is the same, using only "SMART"

    Args:
      underlying_symbol: Symbol of the underlying contract.
      underlying_sec_type: Security type of the underlying contract.
      underlying_con_id: ConID of the underlying contract.
      filters: Dictionary of filters to apply to the options chain.
        - trading_class: List of trading classes to filter by.
        - expirations: List of expirations to filter by.
        - strikes: List of strikes to filter by.
        - rights: List of rights to filter by.


    Returns:
      List of options chain for the given underlying contract.

    """
    try:
      await self._connect()
      chains = await self.ib.reqSecDefOptParamsAsync(
        underlyingSymbol=underlying_symbol,
        futFopExchange="",
        underlyingSecType=underlying_sec_type,
        underlyingConId=underlying_con_id,
      )
      chains = util.df(chains)
      chains = chains[[
        "exchange",
        "underlyingConId",
        "tradingClass",
        "expirations",
        "strikes",
      ]]

      if filters:
        expirations = filters.get("expirations", chains["expirations"].iloc[0])
        strikes = filters.get("strikes", chains["strikes"].iloc[0])
        rights = filters.get("rights", ["C", "P"])
        trading_classes = filters.get("trading_class", chains["tradingClass"].unique())
      else:
        expirations = chains["expirations"].iloc[0]
        strikes = chains["strikes"].iloc[0]
        rights = ["C", "P"]
        trading_classes = chains["tradingClass"].unique()
      contracts = [
        Option(
          symbol=underlying_symbol,
          lastTradeDateOrContractMonth=expiry,
          strike=strike,
          right=right,
          exchange="SMART",
          tradingClass=trading_class,
        )
        for right in rights
        for strike in strikes
        for expiry in expirations
        for trading_class in trading_classes
      ]
      try:
        contracts = await self.ib.qualifyContractsAsync(*contracts, returnAll=True)
        contracts = [c for c in contracts if c is not None]
        contracts = convert_df_columns_to_snake_case(util.df(contracts, labels=[
            "conId", "symbol", "secType", "lastTradeDateOrContractMonth",
            "strike", "right", "multiplier", "exchange", "primaryExchange",
            "currency", "localSymbol", "tradingClass"
        ]))
      except Exception as e:
        logger.warning("Error qualifying contracts: {}", str(e))
        raise
    except Exception as e:
      logger.error("Error getting options chain: {}", str(e))
      raise
    else:
      return contracts.to_dict(orient="records")
