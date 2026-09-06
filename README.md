# IBKR MCP Server

A FastAPI application that provides an MCP (Model Context Protocol) server for Interactive Brokers (IBKR) trading operations. The server automatically manages an IBKR Gateway Docker container and exposes trading functionality through both REST API and MCP endpoints.

## Features

- **Docker Management**: Automatic IBKR Gateway container lifecycle
- **Account Management**: Account summary, positions, and account values
- **Trading Operations**: Place orders, cancel orders, manage open orders
- **Market Data**: Real-time market data, historical data, options chains
- **Contract Management**: Contract details, options chains, scanners
- **Connection Management**: Connection status and reconnection
- **MCP Integration**: All API endpoints automatically exposed as MCP tools via FastMCP
- **Health Monitoring**: Health checks, restarts gateways when no market data

## Quick Start

### Prerequisites

- Python 3.13+
- Docker installed and running
- IBKR account credentials (username + password)

### Credentials Setup

The MCP server reads the IBKR Gateway password from a **host file** that is bind-mounted into the Gateway container at `/run/secrets/tws_password`. The MCP process does **not** read this file — only Docker and the container do. The file permissions depend on the container image's runtime user ID:

| Image | Runtime user | Password file ownership |
|-------|-------------|------------------------|
| `ghcr.io/gnzsnz/ib-gateway` | uid `1000` | `root:1000`, mode `0440` |
| `ghcr.io/gnzsnz/tws-rdesktop` | uid `911` | `root:911`, mode `0440` |

**Recommended setup (default):**

```bash
# Default path is ~/.secrets/ibkr-gateway/<IB_GATEWAY_USERNAME>
sudo install -d -m 0700 -o root -g root ~/.secrets/ibkr-gateway
sudo sh -c 'umask 0177; echo "YOUR_IBKR_PASSWORD" > ~/.secrets/ibkr-gateway/ebljlc158'
sudo chown root:911 ~/.secrets/ibkr-gateway/ebljlc158
sudo chmod 0440 ~/.secrets/ibkr-gateway/ebljlc158
```

This creates a file owned by `root:911` with mode `0440` — readable by the container's uid/gid (`abc`), unreadable by other host users. The MCP server bind-mounts it directly into the container; no temporary copies are made.

**Custom secrets directory:** set `IB_GATEWAY_CREDENTIALS_PATH` in `.env` to override the default `~/.secrets/ib-gateway/`. The MCP server constructs the secret file path as `<IB_GATEWAY_CREDENTIALS_PATH>/<IB_GATEWAY_USERNAME>`:

```bash
IB_GATEWAY_CREDENTIALS_PATH=/secure/secrets   # looks for /secure/secrets/ebljlc158
```

**Custom file path:** set `IB_GATEWAY_PASSWORD_FILE` to use an explicit full path (no username suffix). This takes precedence over `IB_GATEWAY_PASSWORD_PATH`:

```bash
IB_GATEWAY_PASSWORD_FILE=/secure/path/tws_password
```

**Optional abc password file:** set `PASSWORD_FILE` to specify a host path to an additional secret file that will be bind-mounted into the container at `/run/secrets/abc_password` (exposed as `PASSWD_FILE` env var inside the container). Default: `~/.secrets/ib-gateway/abc_password` (or `<IB_GATEWAY_CREDENTIALS_PATH>/abc_password` if that's set). Can also use `--password-file` CLI arg:

```bash
PASSWORD_FILE=/secure/path/abc_password
```

**VNC password file:** set `VNC_PASSWORD_FILE` to specify a host path to a VNC password file that will be bind-mounted read-only into the container at `/run/secrets/vnc_password` (exposed as `VNC_SERVER_PASSWORD_FILE` inside the container). Can also use `--vnc-password-file` CLI arg:

```bash
VNC_PASSWORD_FILE=/secure/path/vnc_password
```

The same permission requirements apply: the file must be readable by the container's uid/gid (`911` for `tws-rdesktop`, `1000` for `ib-gateway`). Modes that work include `0440` (group-readable), `0604` (world-readable, no group/other write), or `0644`.

**Security notes:**

- The password file is the only secret the container needs. Never bake it into a Docker image or commit it to source control.
- The container only sees the file at `/run/secrets/tws_password` (read-only bind mount). It cannot modify it.
- If you previously used the `IB_GATEWAY_PASSWORD` env var directly, that still works but is less secure (visible in `docker inspect`).

### Installation

1. **Clone and setup:**
   ```bash
   git clone <repository-url>
   cd ibkr-mcp-server
   ```

2. **Install dependencies:**
   ```bash
   uv sync
   ```

3. **Run the server:**
   ```bash
   ./run.sh
   ```

   Or manually:
   ```bash
   uv run python main.py --ib-gateway-tradingmode=paper
   ```

   Credentials are loaded from the `.env` file.

The server will start on `http://localhost:8000` with API docs at `/docs`. MCP server will be available at `http://localhost:8000/mcp`.

4. **Troubleshoot**

You can use http://localhost:6080/ for browser based VNC

## Configuration

### Environment Variables (`.env`)

| Variable | Default | Description |
|----------|---------|-------------|
| `IB_GATEWAY_USERNAME` | *(required)* | IBKR Gateway username |
| `IB_GATEWAY_PASSWORD` | *(none)* | IBKR Gateway password (less secure than password file) |
| `IB_GATEWAY_PASSWORD_FILE` | *(none)* | Explicit path to the password file (takes precedence over `IB_GATEWAY_CREDENTIALS_PATH`) |
| `IB_GATEWAY_CREDENTIALS_PATH` | `~/.secrets/ib-gateway` | Directory for password files; path is `<IB_GATEWAY_CREDENTIALS_PATH>/<IB_GATEWAY_USERNAME>` |
| `IB_GATEWAY_DATA_PATH` | `ib-gateway-data` | Base directory for `.docker/` and TWS settings |
| `PASSWORD_FILE` | `~/.secrets/ib-gateway/abc_password` | Host path to abc_password secret file |
| `VNC_PASSWORD_FILE` | `~/.secrets/ib-gateway/vnc_password` | Host path to VNC password secret file |
| `IB_GATEWAY_VNC_PASSWORD` | *(none)* | VNC password (less secure than VNC password file) |
| `IB_GATEWAY_VNC_PORT` | `5900` | Host port for VNC |
| `IB_GATEWAY_IMAGE` | `ghcr.io/gnzsnz/ib-gateway:latest` | Docker image for IBKR Gateway |
| `IB_GATEWAY_TWS_SETTINGS_PATH` | *(image-specific)* | Host path for TWS settings persistence (default: `<IB_GATEWAY_DATA_PATH>/tws_settings` for ib-gateway, `<IB_GATEWAY_DATA_PATH>/config` for tws-rdesktop) |
| `TWS_RDP_PORT` | `3389` | Host port for container-side RDP |
| `MCP_PORT` | `8000` | MCP application port |
| `READ_ONLY_API` | `true` | IBKR Gateway read-only API mode |
| `ENV_FILE` | `.env` | Path to the `.env` file |
| `IB_GATEWAY_TRADINGMODE` | `paper` | Trading mode (`paper` or `live`) |
| `IB_GATEWAY_AUTO_RESTART_TIME` | *(none)* | Auto-restart time for the gateway |
| `IB_GATEWAY_USE_HOST_NETWORK` | `false` | Use Docker host network instead of bridge |
| `IB_GATEWAY_STARTUP_PERIOD` | *(image-specific)* | Startup period in seconds before health checks |
| `IB_CONNECTION_TIMEOUT` | `30` | IB API connection timeout (seconds) |
| `IB_GATEWAY_TIMEOUT` | `300` | Gateway container startup timeout (seconds) |
| `IB_REQUEST_TIMEOUT` | `30` | Request timeout (seconds) |
| `ENABLE_FILE_LOGGING` | `false` | Enable file logging |
| `LOG_FILE_PATH` | `logs/app.log` | Log file location |
| `LOG_LEVEL` | `INFO` | Log level |

**Image passthrough env vars** (passed through to the container only when explicitly set):

| Variable | Description |
|----------|-------------|
| `TWS_ACCEPT_INCOMING` | Accept incoming TWS connections |
| `TWOFA_TIMEOUT_ACTION` | Two-factor authentication timeout action |
| `TWOFA_DEVICE` | Two-factor authentication device |
| `TWOFA_EXIT_INTERVAL` | Two-factor authentication exit interval |
| `RELOGIN_AFTER_TWOFA_TIMEOUT` | Re-login after two-factor timeout |
| `EXISTING_SESSION_DETECTED_ACTION` | Action for existing session detected |
| `BYPASS_WARNING` | Bypass warning |
| `ALLOW_BLIND_TRADING` | Allow blind trading |
| `AUTO_LOGOFF_TIME` | Auto logoff time |
| `TWS_COLD_RESTART` | TWS cold restart |
| `SAVE_TWS_SETTINGS` | Save TWS settings |
| `TIME_ZONE` | Time zone |
| `TWS_SETTINGS_PATH` | TWS settings path |
| `TWS_MASTER_CLIENT_ID` | TWS master client ID |
| `JAVA_HEAP_SIZE` | Java heap size |
| `SSH_TUNNEL` | SSH tunnel |
| `SSH_OPTIONS` | SSH options |
| `SSH_ALIVE_INTERVAL` | SSH alive interval |
| `SSH_ALIVE_COUNT` | SSH alive count |
| `SSH_PASSPHRASE` | SSH passphrase |
| `SSH_PASSPHRASE_FILE` | SSH passphrase file |
| `SSH_REMOTE_PORT` | SSH remote port |
| `SSH_USER_TUNNEL` | SSH user tunnel |
| `SSH_RESTART` | SSH restart |
| `SSH_VNC_PORT` | SSH VNC port |
| `SSH_RDP_PORT` | SSH RDP port |
| `PUID` | Process user ID |
| `PGID` | Process group ID |
| `PASSWD` | Password |
| `PASSWD_FILE` | Password file |
| `START_SCRIPTS` | Start scripts |
| `X_SCRIPTS` | X scripts |
| `IBC_SCRIPTS` | IBC scripts |
| `CUSTOM_CONFIG` | Custom config |
| `TWS_USERID_PAPER` | TWS user ID for paper trading |
| `TWS_PASSWORD_PAPER` | TWS password for paper trading |
| `TWS_PASSWORD_PAPER_FILE` | TWS password file for paper trading |

### CLI Parameters

```
usage: main.py [--mcp-port MCP_PORT] [--log-level LOG_LEVEL] [--mode {PROD,DEV}]
               [--ib-gateway-tradingmode {paper,live}] [--read-only-api READ_ONLY_API]
               [--ib-gateway-vnc-password IB_GATEWAY_VNC_PASSWORD]
               [--ib-gateway-image IB_GATEWAY_IMAGE] [--tws-rdp-port TWS_RDP_PORT]
               [--ib-gateway-data-path IB_GATEWAY_DATA_PATH]
               [--ib-gateway-tws-settings-path IB_GATEWAY_TWS_SETTINGS_PATH]
               [--ib-gateway-credentials-path IB_GATEWAY_CREDENTIALS_PATH]
               [--password-file PASSWORD_FILE] [--vnc-password-file VNC_PASSWORD_FILE]
               [--mcp-transport {streamable-http,sse}] [--ib-gateway-username IB_GATEWAY_USERNAME]
               [--env-file ENV_FILE]
```

| Parameter | Description |
|-----------|-------------|
| `--mcp-port` | MCP application port (default: 8000, or `MCP_PORT` env var) |
| `--log-level` | Log level (default: INFO) |
| `--mode` | Application mode - `PROD` or `DEV` (default: PROD) |
| `--ib-gateway-tradingmode` | Trading mode - `paper` or `live` (default: paper) |
| `--read-only-api` | IBKR Gateway read-only API mode - `true` or `false` (default: true, or `READ_ONLY_API` env var) |
| `--ib-gateway-vnc-password` | VNC password to enable x11vnc inside the gateway container |
| `--ib-gateway-image` | Docker image for IBKR Gateway (default: ghcr.io/gnzsnz/ib-gateway:latest, or `IB_GATEWAY_IMAGE` env var) |
| `--tws-rdp-port` | Host port for container-side RDP (default: 3389, or `TWS_RDP_PORT` env var) |
| `--ib-gateway-data-path` | Base directory for `.docker/` and TWS settings (default: `ib-gateway-data` in current dir, or `IB_GATEWAY_DATA_PATH` env var) |
| `--ib-gateway-tws-settings-path` | Host path for TWS settings persistence (default: `<IB_GATEWAY_DATA_PATH>/tws_settings` for ib-gateway, `<IB_GATEWAY_DATA_PATH>/config` for tws-rdesktop, or `IB_GATEWAY_TWS_SETTINGS_PATH` env var) |
| `--ib-gateway-credentials-path` | Host path for credential files (default: `~/.secrets/ib-gateway`, or `IB_GATEWAY_CREDENTIALS_PATH` env var) |
| `--password-file` | Host path to the abc password file (default: `~/.secrets/ib-gateway/abc_password`, or `PASSWORD_FILE` env var) |
| `--vnc-password-file` | Host path to the VNC password file (default: `~/.secrets/ib-gateway/vnc_password`, or `VNC_PASSWORD_FILE` env var) |
| `--mcp-transport` | MCP transport type - `streamable-http` or `sse` (default: streamable-http) |
| `--ib-gateway-username` | IBKR Gateway username (overrides `IB_GATEWAY_USERNAME` env var) |
| `--env-file` | Path to the .env file (default: ./.env, or `ENV_FILE` env var) |

## API Documentation

All IBKR endpoints are automatically exposed as MCP tools via FastMCP. The API follows RESTful conventions and returns JSON responses.

### Gateway Management

These endpoints provide information about the IBKR Gateway Docker container.

#### `GET /gateway/status`
Get the current status of the IBKR Gateway container.

**Example:**
```bash
curl -X GET "http://localhost:8000/gateway/status"
```

**Response:**
```json
{
  "status": "running",
  "container_id": "a1b2c3d4e5f6",
  "started_at": "2025-10-05T10:00:00Z"
}
```

#### `GET /gateway/logs`
Retrieve the container logs (last 100 lines by default).

**Query Parameters:**
- `tail`: Number of log lines to return (default: 100)

**Example:**
```bash
curl -X GET "http://localhost:8000/gateway/logs?tail=100"
```

---


### Account Management

#### `GET /ibkr/account/summary`
Get a summary of the trading account information.

**Query Parameters:**
- `account_id`: (Optional) Specific account ID. If not provided, uses the default account.

**Example:**
```bash
curl -X GET "http://localhost:8000/ibkr/account/summary"
```

**Response:**
```json
{
  "account_id": "DU1234567",
  "account_type": "INDIVIDUAL",
  "net_liquidation_value": 125000.50,
  "total_cash_value": 25000.75,
  "gross_position_value": 100000.25,
  "unrealized_pnl": 2500.00,
  "realized_pnl": 1500.50,
  "available_funds": 50000.25,
  "excess_liquidity": 52000.75,
  "buying_power": 150000.00,
  "leverage": 1.5
}
```

#### `GET /ibkr/account/positions`
Get detailed information about current positions.

**Example:**
```bash
curl -X GET "http://localhost:8000/ibkr/account/positions"
```

**Response:**
```json
[
  {
    "account": "DU123456",
    "symbol": "AAPL",
    "sec_type": "STK",
    "exchange": "NASDAQ",
    "currency": "USD",
    "position": 100.0,
    "avg_cost": 150.25,
    "market_price": 155.50,
    "market_value": 15550.00,
    "unrealized_pnl": 525.00,
    "realized_pnl": null,
    "contract_id": 265598
  }
]
```

#### `GET /ibkr/account/values`
Get all account values.

**Example:**
```bash
curl -X GET "http://localhost:8000/ibkr/account/values"
```

**Response:**
```json
[
  {
    "account": "DU123456",
    "key": "CashBalance",
    "value": "50000.00",
    "currency": "USD"
  }
]
```

### Trading Operations

#### `POST /ibkr/orders/place`
Place a new order.

**Request Body:**
```json
{
  "contract": {
    "con_id": 12345678
  },
  "order": {
    "action": "BUY",
    "total_quantity": 10,
    "order_type": "LMT",
    "lmt_price": 150.25,
    "time_in_force": "DAY"
  }
}
```

**Example:**
```bash
curl -X POST "http://localhost:8000/ibkr/orders/place" \
  -H "Content-Type: application/json" \
  -d '{
    "contract": {
      "con_id": 12345678
    },
    "order": {
      "action": "BUY",
      "total_quantity": 10,
      "order_type": "LMT",
      "lmt_price": 150.25,
      "time_in_force": "DAY"
    }
  }'
```

**Response:**
```json
{
  "order_id": 987654321,
  "status": "Submitted",
  "symbol": "AAPL",
  "action": "BUY",
  "quantity": 10.0,
  "filled": 0.0,
  "remaining": 10.0,
  "avg_fill_price": null
}
```

#### `DELETE /ibkr/orders/{order_id}`
Cancel an existing order.

#### `GET /ibkr/orders/open`
Get all open orders.

**Example:**
```bash
curl -X GET "http://localhost:8000/ibkr/orders/open"
```

**Response:**
```json
[
  {
    "order_id": 1,
    "symbol": "AAPL",
    "sec_type": "STK",
    "action": "BUY",
    "quantity": 100.0,
    "order_type": "LMT",
    "status": "Submitted",
    "limit_price": 150.00,
    "aux_price": null,
    "filled": 0.0,
    "remaining": 100.0,
    "avg_fill_price": null
  }
]
```

**Path Parameters:**
- `order_id`: The ID of the order to cancel

**Example:**
```bash
curl -X DELETE "http://localhost:8000/ibkr/orders/987654321"
```

**Response:**
```json
{
  "order_id": 987654321,
  "status": "Cancelled",
  "message": "Order cancelled successfully"
}
```

### Market Data

#### `GET /ibkr/market_data/historical`
Get historical market data.

**Query Parameters:**
- `contract_id`: (Optional) Exactly one IBKR contract ID. Recommended for better performance - avoids symbol lookup
- `symbol`: (Optional) The ticker symbol. Required if `contract_id` not provided
- `sec_type`: Security type (e.g., "STK", "OPT", "FUT") - used with symbol
- `exchange`: Exchange (e.g., "SMART", "ISLAND") - used with symbol
- `currency`: Currency (e.g., "USD")
- `duration`: Data duration (e.g., "1 D", "1 W", "1 M", "1 Y")
- `bar_size`: Bar size (e.g., "1 min", "5 mins", "1 hour", "1 day")
- `what_to_show`: Data type (e.g., "TRADES", "MIDPOINT", "BID", "ASK")
- `use_rth`: Use regular trading hours only (true/false)
- `end_date`: (Optional) End date for historical data. Formats:
  - Date only: `YYYYMMDD` (e.g., `20260223`) - converted to `YYYYMMDD 15:59:00 {timezone}`
  - Date with time: `YYYYMMDD HH:MM:SS` (e.g., `20260223 15:30:00`)
  - Full: `YYYYMMDD HH:MM:SS Timezone` (e.g., `20260223 15:30:00 US/Eastern`)

**Note:** Either `symbol` or `contract_id` must be provided. Using `contract_id` is recommended as it avoids symbol lookup and is more efficient.

**Example with contract_id (recommended):**
```bash
curl -X GET "http://localhost:8000/ibkr/market_data/historical?contract_id=265598&duration=1%20D&bar_size=1%20min&what_to_show=TRADES&use_rth=true"
```

**Example with end_date:**
```bash
# Date only - will be converted to end of trading day with timezone
curl -X GET "http://localhost:8000/ibkr/market_data/historical?contract_id=265598&duration=5%20D&bar_size=1%20day&end_date=20260220"

# Date with time - used as-is
curl -X GET "http://localhost:8000/ibkr/market_data/historical?contract_id=265598&duration=5%20D&bar_size=1%20day&end_date=20260220%2015:30:00"
```

**Response:**
```json
[
  {
    "date": "2025-10-05T09:30:00",
    "open": 155.25,
    "high": 155.40,
    "low": 155.10,
    "close": 155.30,
    "volume": 2500,
    "wap": 155.25,
    "count": 125
  },
  {
    "date": "2025-10-05T09:35:00",
    "open": 155.30,
    "high": 155.75,
    "low": 155.25,
    "close": 155.70,
    "volume": 3200,
    "wap": 155.50,
    "count": 150
  }
]
```

#### `GET /ibkr/market_data`
Get real-time market data for a symbol or contract IDs.

**Query Parameters:**
- `symbol`: Symbol to get data for (e.g., AAPL)
- `contract_ids`: (Optional) One or more IBKR contract IDs. Pass multiple times for multiple contracts, e.g., `?contract_ids=265598&contract_ids=123456`
- `sec_type`: Security type (e.g., STK, OPT, FUT) - used with symbol (default: STK)
- `exchange`: Exchange (e.g., SMART, ISLAND) - used with symbol (default: SMART)
- `currency`: Currency (e.g., USD) - used with symbol (default: USD)
- `subscription_type`: Type of market data subscription (realtime or delayed, default: realtime)

**Note:** Either `symbol` or `contract_ids` must be provided. Using `symbol` is recommended for better performance.

**Example with symbol:**
```bash
curl -X GET "http://localhost:8000/ibkr/market_data?symbol=AAPL&subscription_type=delayed" -H "Accept: application/json"
```

**Example with contract_ids:**
```bash
curl -X GET "http://localhost:8000/ibkr/market_data?contract_ids=265598&contract_ids=123456"
```

**Response:**
```json
[
  {
    "contract_id": 265598,
    "symbol": "AAPL",
    "sec_type": "STK",
    "last": 263.55,
    "close": 272.95,
    "bid": null,
    "ask": null,
    "bid_size": null,
    "ask_size": null,
    "high": 272.81,
    "low": 262.89,
     "volume": 724566,
     "mark": null,
     "high_52_week": null,
     "low_52_week": null,
     "open_interest": null,
     "greeks": null,
     "timestamp": "2026-02-28T12:08:47.821499+00:00",
     "last_trade_time": "2026-02-28T12:07:55+00:00",
     "market_data_type": 3
  }
]
```

### Fundamental Data

#### `GET /ibkr/fundamental`
Get fundamental data for a contract, including earnings dates, dividend information, and financial metrics.

**Query Parameters:**
- `contract_id`: (Optional) IBKR contract ID. If provided, symbol lookup is skipped.
- `symbol`: (Optional) Symbol to look up (e.g., AAPL). Required if `contract_id` not provided.
- `sec_type`: Security type (e.g., STK, OPT, FUT) - used with symbol (default: STK)
- `exchange`: Exchange (e.g., SMART, ISLAND) - used with symbol
- `currency`: Currency (e.g., USD) - used with symbol
- `report_type`: Fundamental report type (default: CalendarReport)
  - `CalendarReport`: Earnings dates, dividend calendar
  - `ReportsFinSummary`: Financial summary (P/E, revenue, etc.)
  - `ReportSnapshot`: Company snapshot (ratios, dividend yield)
  - `ReportsFinStatements`: Full financial statements
  - `RESC`: Analyst estimates
  - `ReportsOwnership`: Company ownership

**Note:** Either `symbol` or `contract_id` must be provided. Using `contract_id` is recommended.

**Example - CalendarReport (earnings & dividends):**
```bash
curl -X GET "http://localhost:8000/ibkr/fundamental?symbol=AAPL&report_type=CalendarReport"
```

**Response:**
```json
{
  "contract_id": 265598,
  "symbol": "AAPL",
  "sec_type": "STK",
  "report_type": "CalendarReport",
  "next_earnings_date": "2025-01-15",
  "earnings_estimate": 1.45,
  "earnings_actual": 1.50,
  "earnings_history": [
    {"period": "2024-10-15", "estimate": 1.30, "actual": 1.35}
  ],
  "dividend_yield": null,
  "next_dividend": {
    "ex_date": "2025-01-10",
    "pay_date": "2025-01-20",
    "amount": 0.24
  },
  "dividend_history": [
    {"ex_date": "2024-10-10", "pay_date": "2024-10-20", "amount": 0.24}
  ],
  "pe_ratio": null,
  "raw_xml": "..."
}
```

**Example - ReportSnapshot (financial metrics):**
```bash
curl -X GET "http://localhost:8000/ibkr/fundamental?contract_id=265598&report_type=ReportSnapshot"
```

**Response:**
```json
{
  "contract_id": 265598,
  "symbol": "AAPL",
  "sec_type": "STK",
  "report_type": "ReportSnapshot",
  "next_earnings_date": null,
  "pe_ratio": 28.5,
  "dividend_yield": 0.006,
  "market_cap": 1750000000000.0,
  "sector": "Technology",
  "full_name": "Apple Inc.",
  "raw_xml": "..."
}
```

### Contract Management

#### `GET /ibkr/contract_details`
Get detailed information about a contract.

**Query Parameters:**
- `symbol`: The symbol (e.g., AAPL)
- `sec_type`: Security type (e.g., STK, OPT, FUT)
- `exchange`: Exchange (e.g., SMART, ISLAND)
- `primary_exchange`: Primary exchange (e.g., NASDAQ, NYSE)
- `currency`: Currency (e.g., USD)
- `options`: Optional parameters as JSON string including:
  - `last_trade_date_or_contract_month`: Expiry date for options - "YYYYMMDD"
  - `strike`: Strike price (for options)
  - `right`: Right for options - "C" or "P"
  - `trading_class`: Trading class (e.g., SPXW for weekly SPX options)

**Returns:**
- `qualified_contract`: A single contract dict when a unique match is found
- `candidate_contracts`: A list of contract candidates when multiple matches exist
- `error`: Error message when the request fails

**Example - Qualified Contract (single match):**
When the query is specific enough (e.g., includes currency), a single qualified contract is returned:
```bash
curl -X GET "http://localhost:8000/ibkr/contract_details?symbol=CCJ&sec_type=STK&exchange=SMART&currency=USD"
```

**Response:**
```json
{
  "qualified_contract": {
    "sec_type": "STK",
    "con_id": 1447060,
    "symbol": "CCJ",
    "last_trade_date_or_contract_month": "",
    "strike": 0.0,
    "right": "",
    "multiplier": "",
    "exchange": "SMART",
    "primary_exchange": "NYSE",
    "currency": "USD",
    "local_symbol": "CCJ",
    "trading_class": "CCJ",
    "include_expired": false,
    "sec_id_type": "",
    "sec_id": "",
    "description": "",
    "issuer_id": "",
    "combo_legs_descrip": "",
    "combo_legs": [],
    "delta_neutral_contract": null
  }
}
```

**Example - Candidate Contracts (ambiguous match):**
When the query is ambiguous (e.g., missing currency), multiple contract candidates are returned:
```bash
curl -X GET "http://localhost:8000/ibkr/contract_details?symbol=CCJ&sec_type=STK&exchange=SMART"
```

**Response:**
```json
{
  "candidate_contracts": [
    {
      "sec_type": "STK",
      "con_id": 1447060,
      "symbol": "CCJ",
      "last_trade_date_or_contract_month": "",
      "strike": 0.0,
      "right": "",
      "multiplier": "",
      "exchange": "SMART",
      "primary_exchange": "NYSE",
      "currency": "USD",
      "local_symbol": "CCJ",
      "trading_class": "CCJ",
      "include_expired": false,
      "sec_id_type": "",
      "sec_id": "",
      "description": "",
      "issuer_id": "",
      "combo_legs_descrip": "",
      "combo_legs": [],
      "delta_neutral_contract": null
    },
    {
      "sec_type": "STK",
      "con_id": 81540716,
      "symbol": "CCJ",
      "last_trade_date_or_contract_month": "",
      "strike": 0.0,
      "right": "",
      "multiplier": "",
      "exchange": "SMART",
      "primary_exchange": "FWB2",
      "currency": "EUR",
      "local_symbol": "CCJ",
      "trading_class": "XETRA",
      "include_expired": false,
      "sec_id_type": "",
      "sec_id": "",
      "description": "",
      "issuer_id": "",
      "combo_legs_descrip": "",
      "combo_legs": [],
      "delta_neutral_contract": null
    }
  ]
}
```

#### `GET /ibkr/options_chain`
Get options chain for a given underlying contract.

**Query Parameters:**
- `underlying_symbol`: Symbol of the underlying contract (e.g., CCJ)
- `underlying_sec_type`: Security type of the underlying contract (e.g., STK)
- `underlying_con_id`: ConID of the underlying contract (e.g., 1447060)
- `exchange`: Exchange to filter chains by (e.g., SMART, CBOE). If not specified and multiple chains are available, returns a list of candidate chains.
- `filters`: Dictionary of filters to apply to the options chain (optional). You must specify at least one filter (including expirations) to reduce the number of options in the chain.
  - `trading_class`: List of trading classes to filter by (e.g., ["CCJ"])
  - `expirations`: List of expirations to filter by (e.g., ["20270206"])
  - `strikes`: List of strikes to filter by (e.g., [120])
  - `rights`: List of rights to filter by (e.g., ["C"] for calls, ["P"] for puts)

**Returns:**
- `options_chain`: List of option contracts when a single chain is found and filters are provided
- `candidate_chains`: List of candidate chains when multiple matches exist or no filters are provided
- `error`: Error message when the request fails

**Example 1 - Multiple Candidate Chains (no exchange specified):**
When no exchange is specified and multiple option chains exist for different exchanges:
```bash
curl "http://localhost:8000/ibkr/options_chain?underlying_symbol=CCJ&underlying_sec_type=STK&underlying_con_id=1447060"
```

**Response:**
```json
{
  "candidate_chains": [
    {
      "exchange": "BOX",
      "underlying_con_id": "1447060",
      "trading_class": "CCJ",
      "expirations": ["20260206", "20260213", "20260220", "20260227", "20260306", "20260313", "20260320", "20260618", "20260918", "20261218", "20270115", "20280121"],
      "strikes": [20.0, 23.0, 25.0, 28.0, 30.0, 33.0, 35.0, 38.0, 40.0, 42.0, 45.0, 47.0, 50.0, 55.0, 60.0, 65.0, 70.0, 75.0, 79.0, 80.0, 81.0, 82.0, 83.0, 84.0, 85.0, 86.0, 87.0, 88.0, 89.0, 90.0, 91.0, 92.0, 93.0, 94.0, 95.0, 96.0, 97.0, 98.0, 99.0, 100.0, 101.0, 102.0, 103.0, 104.0, 105.0, 106.0, 107.0, 108.0, 109.0, 110.0, 111.0, 112.0, 113.0, 114.0, 115.0, 116.0, 117.0, 118.0, 119.0, 120.0, 121.0, 122.0, 123.0, 124.0, 125.0, 126.0, 127.0, 128.0, 129.0, 130.0, 131.0, 132.0, 133.0, 134.0, 135.0, 136.0, 137.0, 138.0, 139.0, 140.0, 141.0, 142.0, 143.0, 144.0, 145.0, 146.0, 147.0, 148.0, 149.0, 150.0, 152.5, 155.0, 157.5, 160.0, 162.5, 165.0, 170.0, 175.0, 180.0, 185.0, 190.0, 195.0]
    },
    {
      "exchange": "NASDAQOM",
      "underlying_con_id": "1447060",
      "trading_class": "CCJ",
      "expirations": ["20260206", "20260213", "20260220", "20260227", "20260306", "20260313", "20260320", "20260618", "20260918", "20261218", "20270115", "20280121"],
      "strikes": [20.0, 23.0, 25.0, 28.0, 30.0, 33.0, 35.0, 38.0, 40.0, 42.0, 45.0, 47.0, 50.0, 55.0, 60.0, 65.0, 70.0, 75.0, 79.0, 80.0, 81.0, 82.0, 83.0, 84.0, 85.0, 86.0, 87.0, 88.0, 89.0, 90.0, 91.0, 92.0, 93.0, 94.0, 95.0, 96.0, 97.0, 98.0, 99.0, 100.0, 101.0, 102.0, 103.0, 104.0, 105.0, 106.0, 107.0, 108.0, 109.0, 110.0, 111.0, 112.0, 113.0, 114.0, 115.0, 116.0, 117.0, 118.0, 119.0, 120.0, 121.0, 122.0, 123.0, 124.0, 125.0, 126.0, 127.0, 128.0, 129.0, 130.0, 131.0, 132.0, 133.0, 134.0, 135.0, 136.0, 137.0, 138.0, 139.0, 140.0, 141.0, 142.0, 143.0, 144.0, 145.0, 146.0, 147.0, 148.0, 149.0, 150.0, 152.5, 155.0, 157.5, 160.0, 162.5, 165.0, 170.0, 175.0, 180.0, 185.0, 190.0, 195.0]
    }
  ]
}
```

**Example 2 - Single Candidate Chain (exchange specified, but no filters):**
When an exchange is specified but no filters are provided (filters are required to return specific option contracts):
```bash
curl "http://localhost:8000/ibkr/options_chain?underlying_symbol=CCJ&underlying_sec_type=STK&underlying_con_id=1447060&exchange=SMART"
```

**Response:**
```json
{
  "candidate_chains": [
    {
      "exchange": "SMART",
      "underlying_con_id": "1447060",
      "trading_class": "CCJ",
      "expirations": ["20260206", "20260213", "20260220", "20260227", "20260306", "20260313", "20260320", "20260618", "20260918", "20261218", "20270115", "20280121"],
      "strikes": [20.0, 23.0, 25.0, 28.0, 30.0, 33.0, 35.0, 38.0, 40.0, 42.0, 45.0, 47.0, 50.0, 55.0, 60.0, 65.0, 70.0, 75.0, 79.0, 80.0, 81.0, 82.0, 83.0, 84.0, 85.0, 86.0, 87.0, 88.0, 89.0, 90.0, 91.0, 92.0, 93.0, 94.0, 95.0, 96.0, 97.0, 98.0, 99.0, 100.0, 101.0, 102.0, 103.0, 104.0, 105.0, 106.0, 107.0, 108.0, 109.0, 110.0, 111.0, 112.0, 113.0, 114.0, 115.0, 116.0, 117.0, 118.0, 119.0, 120.0, 121.0, 122.0, 123.0, 124.0, 125.0, 126.0, 127.0, 128.0, 129.0, 130.0, 131.0, 132.0, 133.0, 134.0, 135.0, 136.0, 137.0, 138.0, 139.0, 140.0, 141.0, 142.0, 143.0, 144.0, 145.0, 146.0, 147.0, 148.0, 149.0, 150.0, 152.5, 155.0, 157.5, 160.0, 162.5, 165.0, 170.0, 175.0, 180.0, 185.0, 190.0, 195.0]
    }
  ]
}
```

**Example 3 - Options Chain (exchange and filters provided):**
When both an exchange is specified and filters are provided, specific option contracts are returned:
```bash
curl "http://localhost:8000/ibkr/options_chain?underlying_symbol=CCJ&underlying_sec_type=STK&underlying_con_id=1447060&exchange=SMART&filters=%7B%22trading_class%22%3A%5B%22CCJ%22%5D%2C%22expirations%22%3A%5B%2220270115%22%2C%2220280121%22%5D%2C%22strikes%22%3A%5B120%2C130%5D%2C%22rights%22%3A%5B%22C%22%2C%22P%22%5D%7D"
```

**Response:**
```json
{
  "options_chain": [
    {
      "sec_type": "OPT",
      "con_id": 814588219,
      "symbol": "CCJ",
      "last_trade_date_or_contract_month": "20270115",
      "strike": 120.0,
      "right": "C",
      "multiplier": "100",
      "exchange": "SMART",
      "primary_exchange": "",
      "currency": "USD",
      "local_symbol": "CCJ   270115C00120000",
      "friendly_symbol": "CCJ Jan15'27 120.0 CALL",
      "trading_class": "CCJ",
      "include_expired": false,
      "sec_id_type": "",
      "sec_id": "",
      "description": "",
      "issuer_id": "",
      "combo_legs_descrip": "",
      "combo_legs": [],
      "delta_neutral_contract": null
    },
    {
      "sec_type": "OPT",
      "con_id": 814233597,
      "symbol": "CCJ",
      "last_trade_date_or_contract_month": "20280121",
      "strike": 120.0,
      "right": "C",
      "multiplier": "100",
      "exchange": "SMART",
      "primary_exchange": "",
      "currency": "USD",
      "local_symbol": "CCJ   280121C00120000",
      "friendly_symbol": "CCJ Jan21'28 120.0 CALL",
      "trading_class": "CCJ",
      "include_expired": false,
      "sec_id_type": "",
      "sec_id": "",
      "description": "",
      "issuer_id": "",
      "combo_legs_descrip": "",
      "combo_legs": [],
      "delta_neutral_contract": null
    },
    {
      "sec_type": "OPT",
      "con_id": 817259062,
      "symbol": "CCJ",
      "last_trade_date_or_contract_month": "20270115",
      "strike": 130.0,
      "right": "C",
      "multiplier": "100",
      "exchange": "SMART",
      "primary_exchange": "",
      "currency": "USD",
      "local_symbol": "CCJ   270115C00130000",
      "friendly_symbol": "CCJ Jan15'27 130.0 CALL",
      "trading_class": "CCJ",
      "include_expired": false,
      "sec_id_type": "",
      "sec_id": "",
      "description": "",
      "issuer_id": "",
      "combo_legs_descrip": "",
      "combo_legs": [],
      "delta_neutral_contract": null
    },
    {
      "sec_type": "OPT",
      "con_id": 817259178,
      "symbol": "CCJ",
      "last_trade_date_or_contract_month": "20280121",
      "strike": 130.0,
      "right": "C",
      "multiplier": "100",
      "exchange": "SMART",
      "primary_exchange": "",
      "currency": "USD",
      "local_symbol": "CCJ   280121C00130000",
      "friendly_symbol": "CCJ Jan21'28 130.0 CALL",
      "trading_class": "CCJ",
      "include_expired": false,
      "sec_id_type": "",
      "sec_id": "",
      "description": "",
      "issuer_id": "",
      "combo_legs_descrip": "",
      "combo_legs": [],
      "delta_neutral_contract": null
    },
    {
      "sec_type": "OPT",
      "con_id": 814588293,
      "symbol": "CCJ",
      "last_trade_date_or_contract_month": "20270115",
      "strike": 120.0,
      "right": "P",
      "multiplier": "100",
      "exchange": "SMART",
      "primary_exchange": "",
      "currency": "USD",
      "local_symbol": "CCJ   270115P00120000",
      "friendly_symbol": "CCJ Jan15'27 120.0 PUT",
      "trading_class": "CCJ",
      "include_expired": false,
      "sec_id_type": "",
      "sec_id": "",
      "description": "",
      "issuer_id": "",
      "combo_legs_descrip": "",
      "combo_legs": [],
      "delta_neutral_contract": null
    },
    {
      "sec_type": "OPT",
      "con_id": 814234636,
      "symbol": "CCJ",
      "last_trade_date_or_contract_month": "20280121",
      "strike": 120.0,
      "right": "P",
      "multiplier": "100",
      "exchange": "SMART",
      "primary_exchange": "",
      "currency": "USD",
      "local_symbol": "CCJ   280121P00120000",
      "friendly_symbol": "CCJ Jan21'28 120.0 PUT",
      "trading_class": "CCJ",
      "include_expired": false,
      "sec_id_type": "",
      "sec_id": "",
      "description": "",
      "issuer_id": "",
      "combo_legs_descrip": "",
      "combo_legs": [],
      "delta_neutral_contract": null
    },
    {
      "sec_type": "OPT",
      "con_id": 817259128,
      "symbol": "CCJ",
      "last_trade_date_or_contract_month": "20270115",
      "strike": 130.0,
      "right": "P",
      "multiplier": "100",
      "exchange": "SMART",
      "primary_exchange": "",
      "currency": "USD",
      "local_symbol": "CCJ   270115P00130000",
      "friendly_symbol": "CCJ Jan15'27 130.0 PUT",
      "trading_class": "CCJ",
      "include_expired": false,
      "sec_id_type": "",
      "sec_id": "",
      "description": "",
      "issuer_id": "",
      "combo_legs_descrip": "",
      "combo_legs": [],
      "delta_neutral_contract": null
    },
    {
      "sec_type": "OPT",
      "con_id": 817259236,
      "symbol": "CCJ",
      "last_trade_date_or_contract_month": "20280121",
      "strike": 130.0,
      "right": "P",
      "multiplier": "100",
      "exchange": "SMART",
      "primary_exchange": "",
      "currency": "USD",
      "local_symbol": "CCJ   280121P00130000",
      "friendly_symbol": "CCJ Jan21'28 130.0 PUT",
      "trading_class": "CCJ",
      "include_expired": false,
      "sec_id_type": "",
      "sec_id": "",
      "description": "",
      "issuer_id": "",
      "combo_legs_descrip": "",
      "combo_legs": [],
      "delta_neutral_contract": null
    }
  ]
}
```

### Scanner Operations

#### `GET /ibkr/scanner/workflow`
Get step-by-step workflow for using scanner effectively.

**Example:**
```bash
curl -X GET "http://localhost:8000/ibkr/scanner/workflow"
```

#### `GET /ibkr/scanner/instrument_codes`
Get available scanner instrument codes with descriptions.

**Example:**
```bash
curl -X GET "http://localhost:8000/ibkr/scanner/instrument_codes"
```

#### `GET /ibkr/scanner/location_codes`
Get available scanner location codes with descriptions.

**Example:**
```bash
curl -X GET "http://localhost:8000/ibkr/scanner/location_codes"
```

#### `GET /ibkr/scanner/scan_codes`
Get available scanner scan codes with descriptions.

**Example:**
```bash
curl -X GET "http://localhost:8000/ibkr/scanner/scan_codes"
```

#### `GET /ibkr/scanner/filter_codes`
Get available scanner filter codes with examples and usage hints.

**Example:**
```bash
curl -X GET "http://localhost:8000/ibkr/scanner/filter_codes"
```

#### `GET /ibkr/scanner/results`
Run a market scanner with specified parameters.

**Query Parameters:**
- `instrument_code`: Instrument type (e.g., "STK", "FUT", "OPT"). Call `get_scanner_instrument_codes()` first.
- `location_code`: Location code (e.g., "STK.US", "STK.EU"). Call `get_scanner_location_codes()` first.
- `scan_code`: Scan code for predefined scans (e.g., "TOP_PERC_GAIN", "MOST_ACTIVE"). Call `get_scanner_scan_codes()` first. Must submit `scan_code`; "MOST_ACTIVE" is a good default.
- `filters`: Comma-separated filters in `parameter=value` format to fine-tune `scan_code` results. Call `get_scanner_filter_codes()` first.
  - Examples: `priceAbove=10,marketCapAbove1e6=1000` or `priceAbove=10,avgVolumeAbove=1000000`
- `max_results`: Maximum number of results to return (1-50, default: 50)

**Example:**
```bash
curl -X GET "http://localhost:8000/ibkr/scanner/results?instrument_code=STK&location_code=STK.US&scan_code=TOP_PERC_GAIN&max_results=25"
```

**Response:**
```json
"I found 3 stocks matching the scanner parameters: ['AAPL', 'MSFT', 'GOOGL']"
```

### Connection Management

#### `GET /ibkr/connection/status`
Get the current connection status to IBKR Gateway/TWS.

**Example:**
```bash
curl -X GET "http://localhost:8000/ibkr/connection/status"
```

**Response:**
```json
{
  "connected": true,
  "host": "localhost",
  "port": 8888,
  "client_id": 0,
  "accounts": ["DU123456"]
}
```

#### `POST /ibkr/connection/reconnect`
Reconnect to IBKR Gateway/TWS.

**Example:**
```bash
curl -X POST "http://localhost:8000/ibkr/connection/reconnect"
```

**Response:**
```json
{
  "success": true,
  "message": "Reconnection initiated",
  "timestamp": "2025-10-05T10:25:00Z"
}
```

## Docker Files

The server generates and manages Docker compose files and persists startup timings. By default these are stored under `ib-gateway-data/` in the current directory; override with `IB_GATEWAY_DATA_PATH` env var or `--ib-gateway-data-path` CLI arg.

| File | Description |
|------|-------------|
| `<data_path>/.docker/docker-compose.yml` | Current Docker compose file used to start the container |
| `<data_path>/.docker/docker-compose.last-success.yml` | Last successfully deployed compose file (used for comparison and rotation) |
| `<data_path>/startup-timings.json` | Persisted startup timings per image, used to optimize future startup wait periods |
| `<data_path>/tws_settings/` | TWS settings persistence directory (for `ib-gateway` image) |
| `<data_path>/config/` | TWS settings persistence directory (for `tws-rdesktop` image) |

Compose files are automatically rotated when configuration changes (e.g., image change, port change). On successful container start, the current compose is saved to `docker-compose.last-success.yml` and the startup timing is persisted to `startup-timings.json`.

## Troubleshooting

- **Docker issues**: Ensure Docker daemon is running
- **Port conflicts**: Check if port 8000 is available
- **IBKR connection**: Verify credentials and TWS/Gateway setup
- **Container fails to start / "Permission denied" on the password file**: the file at `IB_GATEWAY_PASSWORD_FILE` must be readable by the container's runtime user (uid `1000` for `ib-gateway`, uid `911` for `tws-rdesktop`). Use `sudo chown root:<uid> <file> && sudo chmod 0440 <file>` (recommended) or `chmod 0604 <file>` for a less strict alternative. See the [Credentials Setup](#credentials-setup) section.
- **API socket never opens (TWS logs show login complete but no `4002` listener)**: confirm with `docker exec ibkr-gateway cat /proc/net/tcp /proc/net/tcp6 | awk '/0A/ {print}'` — TWS often binds only to IPv6 (`[::]:4002`), which is fine because the MCP client connects via `127.0.0.1` and Linux dual-stack routing accepts it. If only an IPv4 listener is missing, the container's socat is unable to forward and `/ibkr/connection/status` will stay `false` until TWS opens the socket.

## Debugging

### Viewing Application Logs

The application logs to both console and file (when enabled). To enable file logging, add to your `.env` file:

```bash
ENABLE_FILE_LOGGING=true
LOG_FILE_PATH=logs/app.log
LOG_LEVEL=INFO
```

View logs in real-time:

```bash
# Watch the log file
tail -f logs/app.log

# Or use the log file path directly
cat logs/app.log
```

### Using curl to Test Endpoints

Start the server:

```bash
./run.sh
```

Then test with curl commands:

```bash
# Check server is running
curl http://localhost:8000/

# Check IBKR Gateway status
curl http://localhost:8000/gateway/status

# Get Gateway container logs
curl http://localhost:8000/gateway/logs?tail=50

# Check connection status
curl http://localhost:8000/ibkr/connection/status

# Get account summary
curl http://localhost:8000/ibkr/account/summary

# Get positions
curl http://localhost:8000/ibkr/account/positions

# Get market data (example with AAPL)
curl "http://localhost:8000/ibkr/market_data?symbol=AAPL"
```

### API Documentation

Full API documentation is available at: http://localhost:8000/docs

MCP server is available at: http://localhost:8000/mcp

## TODO / Future Work

- Have a look at this to: https://github.com/jgalea/ibkr-mcp

## License

MIT License

## Appendix 1: Generic Ticks Reference

The server requests generic ticks alongside real-time market data to enrich the `MarketData` response. The following generic ticks are used (set in `app/services/market_data.py`):

| Tick | Name | Description |
|------|------|-------------|
| 100 | Option Volume | Option volume (put/call) |
| 101 | Option Open Interest | Option open interest (put/call) |
| 104 | Historical Volatility | Historical volatility |
| 106 | Implied Volatility | Option implied volatility |
| 165 | 52-Week High/Low | 52-week high and low prices |
| 221 | Mark Price | Generic mark price |

These map to the `MarketData` response fields as follows:

| Generic Tick | MarketData Field | ib_async Ticker Attribute |
|--------------|------------------|--------------------------|
| 100 | (requested, not mapped by ib_async) | — |
| 101 | (requested, not mapped by ib_async) | — |
| 104 | _valid_value(row["histVolatility"]) | `histVolatility` |
| 106 | _valid_value(row["impliedVolatility"]) | `impliedVolatility` |
| 165 | `high_52_week`, `low_52_week` | `high52`, `low52` |
| 221 | `mark` | `mark` |

**Additional fields not from generic ticks:**

| MarketData Field | ib_async Ticker Attribute | Tick Type |
|------------------|--------------------------|-----------|
| `timestamp` | `time` | 2 (TIME) |
| `last_trade_time` | `lastTimestamp` / `delayedLastTimestamp` | 45 / 88 |
| `volume` | `volume` | 8 (VOLUME) |
| `open_interest` | `openInterest` | 22 (OPEN_INTEREST) |

**Note:** Generic ticks 100 and 101 are requested but not mapped in ib_async's `GENERIC_TICK_MAP`. The `volume` field uses `ticker.volume` (tick type 8) and `open_interest` uses `ticker.openInterest` (tick type 22). For options, these are the per-contract volume and open interest.
