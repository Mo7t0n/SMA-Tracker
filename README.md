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
- **Daily Notifications**: One combined, richly formatted notification per configured time/service, covering all trackers due at that time — not one message per tracker
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

## Installation Via HACS

1. Open Home Assistant
2. Go to **HACS** → **Integrations**
3. Click on **3 dots** and **Custom Repositories** (top right)
4. Enter the repository URL
5. Select **Integration** as the category
6. Click **Download**
7. Restart Home Assistant

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
   - **Daily Notification**: Enable a daily summary notification on trading days
   - **Notification Time**: Time for the daily notification (default: 22:00)
   - **Notification Service**: Home Assistant notify service, e.g. `notify.pushover`
   - **Minimal Notification**: Only show the name, percentage and trend arrow — hides the price/SMA detail lines

> Existing configuration entries are automatically updated with the new notification options. Notifications remain disabled by default and can be enabled later in the integration options.
>
> All of the above — including the display name — can be changed later via **Settings → Devices & Services → SMA Tracker → Configure** on the individual entry.

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

### Daily Notification (optional)

If you want a daily summary by notification service instead of automation, enable the daily notification option in the integration config. The integration sends the notification on trading days at the configured time.

If several trackers share the same notification time and service, they are combined into a **single** message instead of one notification per tracker. Example (as rendered by Pushover, which supports basic HTML):

```text
🟩 DAX: ↑ +2.34 %
    Kurs: 18420.10 EUR
    SMA200: 18004.55 EUR

🟥 S&P 500: ↓ -0.85 %
    Kurs: 5320.12 USD
    SMA200: 5365.90 USD
```

- 🟥/🟨/🟩 mark the same red/yellow/green thresholds as the sensor color coding
- The trend arrow (↑/↓/→) compares the current price to the previous trading day's close
- Name, percentage and arrow are sent in **bold**, with the percentage/arrow colored to match the status square
- **Minimal Notification** (see above) drops the `Kurs`/`SMA` lines and keeps just the first line

> The bold/color formatting relies on Pushover's HTML support (`data: {html: true}`, sent automatically). Other notify services typically ignore the `html` field; if they don't render HTML, the `<b>`/`<font>` tags may show up as literal text.

Notifications are skipped on Saturday and Sunday, since markets are closed. To test the notification flow on a weekend, flip `_DEBUG_IGNORE_WEEKEND` to `True` near the top of `__init__.py` — this is a code-only debug switch, not a UI option, and should not be left enabled.

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
