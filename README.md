# SMA Tracker for Home Assistant

A Home Assistant custom component for tracking the distance between the current price and the Simple Moving Average (SMA) for various stock indices and securities. Data is sourced from Yahoo Finance.

## Features

- **SMA Calculation**: Automatic calculation of Simple Moving Average for configurable periods (2-500 trading days)
- **Distance Display**: Shows the percentage difference between current price and SMA
- **Color Coding**: Intelligent color display based on distance:
  - 🟢 **Green**: > 2% above SMA (well above average)
  - 🟡 **Yellow**: 0% to < 2% above SMA (close to SMA)
  - 🔴 **Red**: ≤ 0% (below or equal to SMA)
- **Yahoo Finance Integration**: Real market data with 2 years of history
- **Flexible Updates**: Configurable update intervals (5-1440 minutes)
- **Multi-Index Support**: Supports any Yahoo Finance symbol

## Supported Symbols

Examples of configurable indices and securities:

- **DAX**: `^GDAXI`
- **S&P 500**: `^GSPC`
- **Nasdaq**: `^IXIC`
- **Dow Jones**: `^DJI`
- **Euro Stoxx 50**: `^STOXX50E`
- **Nikkei 225**: `^N225`
- **Individual Stocks**: e.g., `AAPL`, `MSFT`, `SIEMENS.DE`, etc.

Find more symbols on [Yahoo Finance](https://finance.yahoo.com/).

## Installation

### Via HACS (recommended)

1. Open Home Assistant
2. Go to **HACS** → **Integrations**
3. Click on **+ Explore & Download Repositories** (top right)
4. Enter the repository URL
5. Select **Integration** as the category
6. Click **Download**
7. Restart Home Assistant

### Manual Installation

1. Download the repository
2. Copy the `sma_tracker` folder to your `custom_components` directory:
   ```
   ~/.homeassistant/custom_components/sma_tracker/
   ```
3. Restart Home Assistant

## Configuration

### Via UI (recommended)

1. Go to **Settings** → **Devices & Services**
2. Click **Create Integration**
3. Search for **SMA Tracker**
4. Fill in the configuration fields:
   - **Yahoo Finance Symbol**: e.g., `^GDAXI` for DAX
   - **Display Name (optional)**: e.g., "DAX SMA200"
   - **SMA Period**: Number of trading days for SMA calculation (default: 200)
   - **Update Interval**: How often to update data in minutes (default: 15)

### Configuration Examples

**DAX with SMA200 (update every 15 minutes)**:
- Symbol: `^GDAXI`
- Display Name: `DAX`
- SMA Period: `200`
- Update Interval: `15`

**S&P 500 with SMA50 (update daily)**:
- Symbol: `^GSPC`
- Display Name: `S&P 500`
- SMA Period: `50`
- Update Interval: `1440`

## Entities

After configuration, the integration creates the following entities:

### Sensor: `sensor.{name}_sma{period}_distance`

**Value**: Percentage difference between current price and SMA

**Attributes**:
- `current_price`: Current price
- `sma_value`: Current SMA value
- `symbol`: Yahoo Finance symbol
- `sma_period`: Configured SMA period
- `currency`: Currency of the index

**Colors (RGB)**:
- Green: `(0, 255, 0)` for values > 2%
- Yellow: `(255, 255, 0)` for values 0% to < 2%
- Red: `(255, 0, 0)` for values ≤ 0%

## Automation Examples

### Notification When SMA is Breached

```yaml
automation:
  - alias: "DAX breaches SMA"
    trigger:
      platform: numeric_state
      entity_id: sensor.dax_sma200_distance
      below: 0
    action:
      service: notify.notify
      data:
        message: "DAX has fallen below the SMA200!"
```

### Lovelace Card

```yaml
type: entities
entities:
  - entity: sensor.dax_sma200_distance
    name: DAX SMA200 Distance
```

## Troubleshooting

### Error: "Not enough historical data"

The integration couldn't retrieve enough historical data from Yahoo Finance. This can happen if:
- The symbol doesn't exist
- Yahoo Finance doesn't have 2 years of data for this symbol

**Solution**: Check the Yahoo Finance symbol and consider reducing the SMA period.

### Error: "HTTP 404"

The symbol doesn't exist or is invalid.

**Solution**: Verify the symbol on [Yahoo Finance](https://finance.yahoo.com/).

### Integration Not Loading

- Check the logs in Home Assistant
- Restart Home Assistant

## Frequently Asked Questions

**Q: Why do you use Yahoo Finance?**
A: Yahoo Finance provides free, reliable data for indices and individual stocks without requiring an API key.

**Q: Can I track multiple indices at the same time?**
A: Yes! You can create multiple configuration entries, one for each index.

**Q: How accurate is the SMA calculation?**
A: Very accurate - it's calculated using 2 years of daily data.

**Q: Can I change the SMA period?**
A: Yes, but you need to create a new configuration entry. Each combination of symbol and SMA period is unique.

## License

MIT License - See LICENSE file for details

## Support

For issues, questions, or feature requests, please open an issue on GitHub.

---

**Note**: This integration is a community project and is not supported by Home Assistant or Yahoo Finance.
