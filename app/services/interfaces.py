"""Main IB interface combining all functionality."""
from .market_data import MarketDataClient
from .contracts import ContractClient
from .scanners import ScannerClient
from .positions import PositionClient
from .account import AccountClient
from .trading import TradingClient
from .connection import ConnectionClient

class IBInterface(
  MarketDataClient,
  ContractClient,
  ScannerClient,
  PositionClient,
  AccountClient,
  TradingClient,
  ConnectionClient,
):
  """Main IB interface combining all functionality."""
