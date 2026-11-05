# SMA Tracker for Home Assistant

[![GitHub Release](https://img.shields.io/github/v/release/Mo7t0n/SMA-Tracker?style=for-the-badge&color=%231CB00A)](https://github.com/Mo7t0n/SMA-Tracker/releases)
[![HACS Custom](https://img.shields.io/badge/HACS-Custom-41BDF5?style=for-the-badge)](https://hacs.xyz/docs/faq/custom_repositories/)
[![HACS validation](https://img.shields.io/github/actions/workflow/status/Mo7t0n/SMA-Tracker/validate.yaml?branch=main&label=HACS&style=for-the-badge)](https://github.com/Mo7t0n/SMA-Tracker/actions/workflows/validate.yaml)
[![hassfest](https://img.shields.io/github/actions/workflow/status/Mo7t0n/SMA-Tracker/hassfest.yml?branch=main&label=hassfest&style=for-the-badge)](https://github.com/Mo7t0n/SMA-Tracker/actions/workflows/hassfest.yml)
[![License](https://img.shields.io/github/license/Mo7t0n/SMA-Tracker?style=for-the-badge&label=license)](LICENSE)

Tracks how far a stock index or security trades above or below its [Simple Moving Average](https://en.wikipedia.org/wiki/Moving_average#Simple_moving_average) (SMA) — e.g. the DAX against its 200-day line — as a `sensor` entity in Home Assistant, with optional notifications: a daily summary and an instant buy/sell signal when the price crosses the SMA. Market data comes from [Yahoo Finance](https://finance.yahoo.com/); no API key needed.

## Installation

1. In HACS, open the menu → **Custom repositories**, add `https://github.com/Mo7t0n/SMA-Tracker` with type **Integration**, then download **SMA Tracker** and restart Home Assistant. Or let this button do the adding for you:

   [![Open your Home Assistant instance and open this repository inside HACS.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=Mo7t0n&repository=SMA-Tracker&category=integration)
2. Add the **SMA Tracker** integration under Settings → Devices & services → **Add integration**, or directly:

   [![Open your Home Assistant instance and start setting up SMA Tracker.](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=sma_tracker)
3. Enter a Yahoo Finance symbol and the SMA period. Each symbol/period combination is its own entry — add the integration again to track more.

## Configuration

| Option | Default | Description |
| --- | --- | --- |
| Yahoo Finance symbol | — | e.g. `^GDAXI` for the DAX, see [symbols](#symbols) |
| Display name | symbol | Name used for the sensor and in notifications |
| SMA period | `200` | Trading days in the average (2–500) |
| Update interval | `60` | Minutes between data refreshes (5–1440) |
| Notifications | off | Send a summary every weekday (Mon–Fri) and a [buy/sell signal](#buysell-signal) when the price crosses the SMA |
| Notification time | `22:00` | When the summary is sent |
| Notification service | `notify.pushover` | Any Home Assistant `notify.*` service |
| Minimal notification | off | Only name, percentage and trend arrow — no price/SMA lines |

Everything except the symbol can be changed later under Settings → Devices & services → SMA Tracker → **Configure**; to track another symbol, add a new entry. Changing the SMA period replaces the sensor with a new one named after the new period (e.g. `sensor.dax_sma50_distance` instead of `sensor.dax_sma200_distance`), so update automations and dashboards that use the old one.

### Symbols

Any symbol listed on [Yahoo Finance](https://finance.yahoo.com/) works, for example:

| Index / security | Symbol |
| --- | --- |
| DAX | `^GDAXI` |
| S&P 500 | `^GSPC` |
| Nasdaq Composite | `^IXIC` |
| Dow Jones | `^DJI` |
| Euro Stoxx 50 | `^STOXX50E` |
| Nikkei 225 | `^N225` |
| Single stocks | `AAPL`, `MSFT`, `SIE.DE`, … |

## Features

- **Distance to SMA as a sensor** — `sensor.<name>_sma<period>_distance` holds the percentage the current price is above (positive) or below (negative) the SMA, with these attributes for templates and automations:

  | Attribute | Content |
  | --- | --- |
  | `current_price` | Current market price |
  | `sma_value` | Current SMA value |
  | `symbol` | Yahoo Finance symbol |
  | `sma_period` | Configured SMA period |
  | `currency` | Currency of the symbol |

- **Status at a glance** — the sensor icon and the notification follow three thresholds:

  | Status | Distance | Icon |
  | --- | --- | --- |
  | 🟩 Well above | ≥ 2 % | `mdi:arrow-up-bold-circle` |
  | 🟨 Close to SMA | 0 % to < 2 % | `mdi:arrow-right-bold-circle` |
  | 🟥 At or below | ≤ 0 % | `mdi:arrow-down-bold-circle` |

- **Enough history for any period** — fetches 1, 2 or 5 years of daily closes depending on the SMA period, so even a 500-day SMA has a full window.
- **One combined daily notification** — all trackers that share a notification time and service are bundled into a single message instead of one per tracker.
- **Buy/sell signal** — an immediate notification as soon as the price crosses the SMA in either direction.

## Daily notification

The summary is titled *SMA Tracker Übersicht*, sorted by SMA period, and looks like this (as rendered by Pushover):

```text
🟩 DAX: ↑ +2.34 %
       Kurs: 18420.10 EUR
       SMA200: 18004.55 EUR

🟥 S&P 500: ↓ -0.85 %
       Kurs: 5320.12 USD
       SMA200: 5365.90 USD
```

- The square uses the thresholds above; name, percentage and arrow are bold, the percentage colored to match.
- The arrow (↑ / ↓ / →) compares the price with the one in the last summary sent for that tracker — the previous close for the first one after a restart. Moves under 0.05 % show as →.
- **Minimal notification** keeps only the first line per tracker.
- Formatting relies on HTML (`data: {html: true}`, sent automatically), which Pushover supports. Other notify services may ignore it or show the `<b>`/`<font>` tags as plain text.
- No notification on Saturdays and Sundays. To test on a weekend, set `_DEBUG_IGNORE_WEEKEND = True` in `__init__.py` locally — don't commit it.

## Buy/sell signal

With notifications enabled, each tracker also sends its own message right after the update in which the distance to the SMA changes sign — via the same notification service, independent of the notification time:

```text
SMA Tracker Verkaufssignal
🟥 DAX auf/unter SMA200 gefallen: -0.12 %
       Kurs: 17982.40 EUR
       SMA200: 18004.55 EUR

SMA Tracker Kaufsignal
🟩 DAX über SMA200 gestiegen: +0.08 %
       Kurs: 18018.95 EUR
       SMA200: 18004.55 EUR
```

- **Sell signal** when the distance falls from above 0 % to 0 % or below, **buy signal** when it rises from 0 % or below to above 0 % — the same threshold as the 🟥 status.
- Checked on every data refresh, so the signal arrives at most one update interval after the cross. Weekends are not skipped, since crypto symbols trade then too.
- The last side is saved across restarts: a cross that happened while Home Assistant was down is reported once startup has finished. The very first update of a new tracker, or after changing its SMA period, only sets the baseline and sends nothing.
- If the price keeps hovering around the SMA, every cross triggers a new signal.
- **Minimal notification** keeps only the first line.

## Examples

The built-in [buy/sell signal](#buysell-signal) covers the cross itself. For other thresholds, use an automation — e.g. notify when the DAX falls more than 5 % below its 200-day line:

```yaml
automation:
  - alias: "DAX 5 % below SMA200"
    triggers:
      - trigger: numeric_state
        entity_id: sensor.dax_sma200_distance
        below: -5
    actions:
      - action: notify.notify
        data:
          message: "DAX is more than 5 % below its SMA200 ({{ states('sensor.dax_sma200_distance') }} %)."
```

Show several trackers on a dashboard:

```yaml
type: entities
title: Markets vs. SMA
entities:
  - entity: sensor.dax_sma200_distance
  - entity: sensor.s_p_500_sma200_distance
```

## Troubleshooting

| Problem | Cause and fix |
| --- | --- |
| *Not enough historical data* | Yahoo Finance has fewer daily closes for the symbol than the SMA period needs (e.g. a recent IPO). Use a shorter period. |
| *HTTP 404* | The symbol doesn't exist. Check the exact spelling on [Yahoo Finance](https://finance.yahoo.com/), including prefixes like `^` and suffixes like `.DE`. |
| No notification | Check that the notify service exists (Developer tools → Actions). The daily summary is only sent on weekdays; a buy/sell signal only after the distance changes sign, not for the first reading of a new tracker or after an SMA period change. Failures are logged under Settings → System → Logs. |

## Support

Found a bug or missing a feature? [Open an issue](https://github.com/Mo7t0n/SMA-Tracker/issues/new/choose).

## License

[GPL-3.0](LICENSE). Not affiliated with Home Assistant or Yahoo Finance.
