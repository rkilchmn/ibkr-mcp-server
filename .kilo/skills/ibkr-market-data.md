# IBKR Market Data & Historical Data

Use these tools to retrieve real-time quotes, options chains, and historical OHLCV bars.

## Tools

- `ibkr_get_market_data` — real-time or delayed market data snapshot
- `ibkr_get_historical_data` — historical OHLCV bars
- `ibkr_get_filtered_options_chain` — options chain filtered by criteria

## Market Data (`ibkr_get_market_data`)

### Parameters

- `contract_ids`: single int or list of ints (preferred, avoids symbol lookup)
- `symbol`: ticker symbol (optional if `contract_ids` provided)
- `sec_type`: default `STK`
- `exchange`: default `SMART`
- `currency`: default `USD`
- `subscription_type`: `realtime` or `delayed`

### Examples

Snapshot by contract ID:
```json
{
  "contract_ids": 265598
}
```

Snapshot by symbol:
```json
{
  "symbol": "AAPL",
  "subscription_type": "delayed"
}
```

Multiple contract IDs:
```json
{
  "contract_ids": [900291907, 908773369]
}
```

## Historical Data (`ibkr_get_historical_data`)

### Parameters

- `contract_id`: contract ID (preferred)
- `symbol`: ticker symbol (optional if `contract_id` provided)
- `sec_type`: default `STK`
- `exchange`: default `SMART`
- `currency`: default `USD`
- `duration`: e.g. `1 D`, `1 W`, `1 M`, `1 Y`
- `bar_size`: e.g. `1 min`, `5 mins`, `1 hour`, `1 day`
- `what_to_show`: `TRADES`, `MIDPOINT`, `BID`, `ASK`
- `use_rth`: `true` or `false`
- `end_date`: optional end date/time

### End Date Formats

| Format | Example | Result |
|--------|---------|--------|
| Date only | `20260821` | Converted to market close time + timezone |
| Date + time | `20260821 15:30:00` | Used as-is |
| Date + time + TZ | `20260821 15:30:00 US/Eastern` | Used as-is |

### Examples

Last month of daily bars:
```json
{
  "contract_id": 344809106,
  "duration": "1 M",
  "bar_size": "1 day"
}
```

Today with 15-minute bars:
```json
{
  "contract_id": 344809106,
  "duration": "1 D",
  "bar_size": "15 mins"
}
```

Specific end date:
```json
{
  "contract_id": 344809106,
  "duration": "1 D",
  "bar_size": "1 day",
  "end_date": "20260821 15:59:00 US/Eastern"
}
```

## Filtered Options Chain (`ibkr_get_filtered_options_chain`)

### Parameters

- `underlying_symbol`: e.g. `GDX`
- `underlying_sec_type`: e.g. `STK`
- `underlying_con_id`: conId of the underlying
- `exchange`: e.g. `SMART`
- `filters`: JSON string, e.g. `{"expirations": ["20260828"], "rights": ["P"], "strikes": [89, 90]}`
- `criteria`: JSON string, e.g. `{"min_delta": -0.1, "max_delta": -0.05}`

### Available Filters

| Filter | Description |
|--------|-------------|
| `trading_class` | List of trading classes, e.g. `["SPXW"]` |
| `expirations` | List of expiry dates `YYYYMMDD` |
| `strikes` | List of strike prices |
| `rights` | List of option rights, `["C"]` or `["P"]` |

### Available Criteria

| Criterion | Description |
|-----------|-------------|
| `min_delta` / `max_delta` | Delta range |
| `min_gamma` / `max_gamma` | Gamma range |
| `min_vega` / `max_vega` | Vega range |
| `min_theta` / `max_theta` | Theta range |
| `min_iv` / `max_iv` | Implied volatility range |

### Examples

GDX puts 89-90 for next week with delta -0.10 to -0.05:
```json
{
  "underlying_symbol": "GDX",
  "underlying_sec_type": "STK",
  "underlying_con_id": 229726316,
  "filters": {"expirations": ["20260828"], "rights": ["P"], "strikes": [89, 90]},
  "criteria": {"min_delta": -0.1, "max_delta": -0.05}
}
```

## Notes

- Prefer `contract_id` over `symbol` for better performance and fewer lookup errors.
- `end_date` with date-only format (`YYYYMMDD`) uses the contract's `liquidHours` to determine market close time. If `liquidHours` is unavailable, it falls back to `15:59:00 US/Eastern`.
- The scanner `liquidHours` format from IB is `YYYYMMDD:HHMM-YYYYMMDD:HHMM` (not `YYYYMMDD:HHMM-HHMM`). The server handles this internally.
- Market data may return `null` bid/ask if only delayed data is available or the subscription is insufficient.
- All market data endpoints require an active IBKR Gateway connection.
