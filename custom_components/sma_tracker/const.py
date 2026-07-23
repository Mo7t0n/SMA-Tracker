"""Constants for the SMA Tracker (Yahoo Finance) integration."""

DOMAIN = "sma_tracker"

CONF_SYMBOL = "symbol"
CONF_NAME = "name"
CONF_SMA_PERIOD = "sma_period"
CONF_SCAN_INTERVAL = "scan_interval"

DEFAULT_SMA_PERIOD = 200
DEFAULT_SCAN_INTERVAL = 60  # minutes

ATTR_CURRENT_PRICE = "current_price"
ATTR_SMA_VALUE = "sma_value"
ATTR_SYMBOL = "symbol"
ATTR_SMA_PERIOD = "sma_period"
ATTR_CURRENCY = "currency"

YAHOO_CHART_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"

# Range of historical data requested from Yahoo Finance.
# 2 years of daily candles is enough headroom for SMA periods up to ~500.
YAHOO_RANGE = "2y"
YAHOO_INTERVAL = "1d"
