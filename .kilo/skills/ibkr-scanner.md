# IBKR Scanner Usage

Use the IBKR scanner tools to discover securities matching market criteria. The scanner ranks instruments by predefined scans and optional filters.

## Workflow

1. Get valid codes (optional but recommended): `ibkr_get_scanner_instrument_codes`, `ibkr_get_scanner_location_codes`, `ibkr_get_scanner_scan_codes`, `ibkr_get_scanner_filter_codes`
2. Execute scan: `ibkr_get_scanner_results`
3. Use `ibkr_get_scanner_workflow` for the full step-by-step guide.

## Parameters

- `instrument_code`: security type, e.g. `STK`, `OPT`, `FUT`, `IND`, `CASH`
- `location_code`: market/region, e.g. `STK.US.MAJOR`, `STK.EU`, `FUT.CME`, `OPT.CBOE`
- `scan_code`: predefined scan type
- `filters`: comma-separated `param=value` pairs to refine results
- `max_results`: 1-50

## Common Scan Codes

| Code | Description |
|------|-------------|
| `TOP_PERC_GAIN` | Highest % gainers |
| `TOP_PERC_LOSE` | Highest % losers |
| `MOST_ACTIVE` | Highest trading volume |
| `OPT_VOLUME_MOST_ACTIVE` | Stocks/ETFs with highest options volume |
| `HOT_BY_VOLUME` | Unusual volume |
| `HIGH_OPT_IMP_VOLAT` | Highest implied volatility |
| `LOW_OPT_IMP_VOLAT` | Lowest implied volatility |
| `TOP_OPEN_PERC_GAIN` | Biggest opening gainers |
| `HIGH_VS_52W_HL` | Near 52-week highs |
| `LOW_VS_52W_HL` | Near 52-week lows |

## Common Filters

| Filter | Example |
|--------|---------|
| `priceAbove` | `priceAbove=10` |
| `marketCapAbove1e6` | `marketCapAbove1e6=1000` (1B cap) |
| `avgVolumeAbove` | `avgVolumeAbove=1000000` |
| `optVolumeAbove` | `optVolumeAbove=5000` |

## Examples

Top percentage gainers in US stocks:
```json
{
  "instrument_code": "STK",
  "location_code": "STK.US.MAJOR",
  "scan_code": "TOP_PERC_GAIN",
  "max_results": 25
}
```

Most active options by volume:
```json
{
  "instrument_code": "STK",
  "location_code": "STK.US.MAJOR",
  "scan_code": "OPT_VOLUME_MOST_ACTIVE",
  "max_results": 25
}
```

With filters:
```json
{
  "instrument_code": "STK",
  "location_code": "STK.US.MAJOR",
  "scan_code": "TOP_PERC_GAIN",
  "filters": "priceAbove=10,avgVolumeAbove=1000000",
  "max_results": 25
}
```

## Notes

- `OPT_VOLUME_MOST_ACTIVE` works with `instrument_code=STK` + `STK.US.MAJOR` to rank stocks by their options volume.
- Some endpoints return errors for certain instrument/location combinations; if `OPT` + `OPT.CBOE` returns empty, try `STK` + `STK.US.MAJOR` with the same scan code.
- The scanner requires an active IBKR Gateway connection.
