"""Fundamental data operations."""
import asyncio
import xml.etree.ElementTree as ET
from ib_async.contract import Contract

from .client import IBClient
from app.core.setup_logging import logger
from app.models import FundamentalData, EarningsEvent, Dividend


class FundamentalClient(IBClient):
  """Fundamental data operations.

  Available public methods:
    - get_fundamental_data: get fundamental data for a contract

  """

  FUNDAMENTAL_REPORT_TYPES = [
    "ReportsFinSummary",
    "ReportsOwnership",
    "ReportSnapshot",
    "ReportsFinStatements",
    "RESC",
    "CalendarReport",
  ]

  async def get_fundamental_data(
    self,
    contract_id: int | None = None,
    symbol: str | None = None,
    sec_type: str | None = "STK",
    exchange: str | None = None,
    currency: str | None = None,
    report_type: str | None = None,
  ) -> FundamentalData | dict:
    """Get fundamental data for a contract.

    Args:
      contract_id: IBKR contract ID. If provided, symbol lookup is skipped.
      symbol: Symbol to look up (e.g., AAPL). Required if contract_id not provided.
      sec_type: Security type (e.g., STK, OPT, FUT).
      exchange: Exchange (e.g., SMART, ISLAND).
      currency: Currency (e.g., USD).
      report_type: Fundamental report type. Defaults to "CalendarReport".
        Options: ReportsFinSummary, ReportsOwnership, ReportSnapshot,
        ReportsFinStatements, RESC, CalendarReport.

    Returns:
      FundamentalData object with parsed fields and raw XML.

    """
    try:
      await self._connect()

      if report_type is None:
        report_type = "CalendarReport"

      if report_type not in self.FUNDAMENTAL_REPORT_TYPES:
        raise ValueError(
          f"Invalid report_type '{report_type}'. "
          f"Valid types: {self.FUNDAMENTAL_REPORT_TYPES}"
        )

      if contract_id is not None:
        contract = Contract(conId=contract_id)
      else:
        if symbol is None:
          raise ValueError("Either contract_id or symbol must be provided")
        contract = Contract(
          symbol=symbol,
          secType=sec_type or "STK",
          exchange=exchange or "",
          currency=currency or "",
        )

      qualified = await asyncio.wait_for(
        self.ib.qualifyContractsAsync(contract, returnAll=True),
        timeout=self.config.ib_request_timeout,
      )
      qualified = [c for c in qualified if c is not None]

      if isinstance(qualified, list) and qualified and isinstance(qualified[0], list):
        candidate_list = qualified[0]
        qualified = [c for c in candidate_list if c is not None]
        qualified = [
          c for c in qualified
          if (exchange is None or c.exchange == exchange)
          and (currency is None or c.currency == currency)
          and (sec_type is None or c.secType == sec_type)
        ]

      if not qualified:
        raise ValueError(
          f"Could not qualify contract for symbol={symbol}, contract_id={contract_id}"
        )
      contract = qualified[0]

      logger.debug(
        "Requesting fundamental data: report_type={report_type}, contract_id={con_id}",
        report_type=report_type,
        con_id=contract.conId,
      )

      xml_data = await asyncio.wait_for(
        self.ib.reqFundamentalDataAsync(
          contract,
          reportType=report_type,
        ),
        timeout=self.config.ib_request_timeout,
      )

      if not isinstance(xml_data, str):
        xml_data = str(xml_data) if xml_data else ""

      if not xml_data or not xml_data.strip():
        return FundamentalData(
          contract_id=contract.conId,
          symbol=contract.symbol,
          sec_type=contract.secType,
          report_type=report_type,
          raw_xml=xml_data or None,
        )

      return self._parse_fundamental_xml(
        xml_data=xml_data,
        contract_id=contract.conId,
        symbol=contract.symbol,
        sec_type=contract.secType,
        report_type=report_type,
      )

    except asyncio.TimeoutError:
      logger.error("Timeout requesting fundamental data for contract_id={contract_id}", contract_id=contract_id)
      raise
    except Exception as e:
      logger.error("Error getting fundamental data: {!s}", str(e))
      raise

  def _parse_fundamental_xml(
    self,
    xml_data: str,
    contract_id: int,
    symbol: str,
    sec_type: str,
    report_type: str,
  ) -> FundamentalData:
    """Parse IBKR fundamental data XML into a FundamentalData model.

    Args:
      xml_data: Raw XML string from IBKR.
      contract_id: Contract ID.
      symbol: Symbol.
      sec_type: Security type.
      report_type: Report type that was requested.

    Returns:
      FundamentalData with parsed fields.

    """
    result = FundamentalData(
      contract_id=contract_id,
      symbol=symbol,
      sec_type=sec_type,
      report_type=report_type,
      raw_xml=xml_data,
    )

    if not xml_data:
      return result

    try:
      root = ET.fromstring(xml_data)
    except ET.ParseError:
      logger.warning("Failed to parse fundamental XML for symbol={symbol}", symbol=symbol)
      return result

    report = self._get_report_root(root, report_type)
    if report is None:
      return result

    if report_type == "CalendarReport":
      self._parse_calendar_report(report, result)
    elif report_type in ("ReportsFinSummary", "ReportSnapshot"):
      self._parse_fundamental_summary(report, result)

    return result

  def _get_report_root(self, root: ET.Element, report_type: str) -> ET.Element | None:
    """Find the root element for a given report type."""
    tag_map = {
      "CalendarReport": "CalendarReport",
      "ReportsFinSummary": "FinancialSummary",
      "ReportSnapshot": "Snapshot",
      "ReportsOwnership": "Ownership",
      "ReportsFinStatements": "FinancialStatements",
      "RESC": "AnalystEstimates",
    }
    tag = tag_map.get(report_type, report_type)

    elem = root.find(f".//{tag}")
    if elem is not None:
      return elem

    if root.tag == tag:
      return root

    return root

  def _parse_calendar_report(self, report: ET.Element, result: FundamentalData) -> None:
    """Parse CalendarReport XML for earnings dates and dividends."""
    earnings = report.find(".//Earnings")
    if earnings is not None:
      history_events = []
      for period_elem in earnings.findall("./Period"):
        period = period_elem.text or None
        estimate = self._find_float(earnings, "./Estimate")
        actual = self._find_float(earnings, "./Actual")

        event = EarningsEvent(
          period=period,
          estimate=estimate,
          actual=actual,
        )
        history_events.append(event)
        if period and result.next_earnings_date is None:
          result.next_earnings_date = period

      if history_events:
        result.earnings_history = history_events

      next_earnings = report.find(".//NextEarningsDate")
      if next_earnings is not None and next_earnings.text:
        result.next_earnings_date = next_earnings.text

    next_earnings = report.find(".//nextEarningsDate")
    if next_earnings is None:
      next_earnings = report.find(".//NextEarningsDate")
    if next_earnings is not None and next_earnings.text:
      result.next_earnings_date = next_earnings.text

    earnings_est = report.find(".//earningsEstimate")
    if earnings_est is None:
      earnings_est = report.find(".//EarningsEstimate")
    if earnings_est is not None and earnings_est.text:
      result.earnings_estimate = self._parse_float(earnings_est.text)

    earnings_actual = report.find(".//earningsActual")
    if earnings_actual is None:
      earnings_actual = report.find(".//EarningsActual")
    if earnings_actual is not None and earnings_actual.text:
      result.earnings_actual = self._parse_float(earnings_actual.text)

    dividends_elem = report.find(".//Dividends")
    if dividends_elem is None:
      dividends_elem = report.find(".//dividends")

    if dividends_elem is not None:
      dividend_history = []
      for div_elem in dividends_elem.findall("./*"):
        ex_date_elem = div_elem.find(".//exDate")
        if ex_date_elem is None:
          ex_date_elem = div_elem.find(".//ExDate")
        pay_date_elem = div_elem.find(".//payDate")
        if pay_date_elem is None:
          pay_date_elem = div_elem.find(".//PayDate")
        amount_elem = div_elem.find(".//amount")
        if amount_elem is None:
          amount_elem = div_elem.find(".//Amount")

        ex_date = ex_date_elem.text if ex_date_elem is not None and ex_date_elem.text else None
        pay_date = pay_date_elem.text if pay_date_elem is not None and pay_date_elem.text else None
        amount = self._parse_float(amount_elem.text) if amount_elem is not None and amount_elem.text else None

        div = Dividend(
          ex_date=ex_date,
          pay_date=pay_date,
          amount=amount,
        )
        dividend_history.append(div)

        if ex_date and result.next_dividend is None:
          result.next_dividend = div

      if dividend_history:
        result.dividend_history = dividend_history

    dividend_yield_elem = report.find(".//dividendYield")
    if dividend_yield_elem is None:
      dividend_yield_elem = report.find(".//dividend_yield")
    if dividend_yield_elem is not None and dividend_yield_elem.text:
      result.dividend_yield = self._parse_float(dividend_yield_elem.text)

  def _parse_fundamental_summary(self, report: ET.Element, result: FundamentalData) -> None:
    """Parse ReportsFinSummary or ReportSnapshot for financial metrics."""
    def _find_text(tag: str) -> str | None:
      elem = report.find(f".//{tag}")
      if elem is None:
        elem = report.find(f".//{tag[0].upper() + tag[1:]}")
      return elem.text if elem is not None and elem.text else None

    result.pe_ratio = self._parse_float(_find_text("peRatio"))
    result.peg_ratio = self._parse_float(_find_text("pegRatio"))
    result.price_to_book = self._parse_float(_find_text("priceToBook"))
    result.price_to_sales = self._parse_float(_find_text("priceToSales"))
    result.market_cap = self._parse_float(_find_text("marketCap"))
    result.dividend_yield = self._parse_float(_find_text("dividendYield"))

    industry_elem = report.find(".//industry")
    if industry_elem is None:
      industry_elem = report.find(".//Industry")
    if industry_elem is not None and industry_elem.text:
      result.industry = industry_elem.text

    sector_elem = report.find(".//sector")
    if sector_elem is None:
      sector_elem = report.find(".//Sector")
    if sector_elem is not None and sector_elem.text:
      result.sector = sector_elem.text

    name_elem = report.find(".//companyName")
    if name_elem is None:
      name_elem = report.find(".//CompanyName")
    if name_elem is not None and name_elem.text:
      result.full_name = name_elem.text

    desc_elem = report.find(".//description")
    if desc_elem is not None and desc_elem.text:
      result.description = desc_elem.text

  def _find_float(self, parent: ET.Element, tag: str) -> float | None:
    elem = parent.find(tag)
    if elem is not None and elem.text:
      return self._parse_float(elem.text)
    return None

  @staticmethod
  def _parse_float(value: str) -> float | None:
    try:
      return float(value)
    except (ValueError, TypeError):
      return None
