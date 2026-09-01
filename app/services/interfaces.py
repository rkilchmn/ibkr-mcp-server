"""Main IB interface combining all functionality."""
from .market_data import MarketDataClient
from .contracts import ContractClient
from .scanners import ScannerClient
from .positions import PositionClient
from .account import AccountClient
from .trading import TradingClient
from .connection import ConnectionClient
from .fundamental import FundamentalClient

class IBInterface(
  MarketDataClient,
  ContractClient,
  ScannerClient,
  PositionClient,
  AccountClient,
  TradingClient,
  ConnectionClient,
  FundamentalClient,
):
  """Main IB interface combining all functionality."""
