"""Constants for the SMA Tracker (Yahoo Finance) integration."""

from datetime import time as dt_time

DOMAIN = "sma_tracker"

CONF_SYMBOL = "symbol"
CONF_NAME = "name"
CONF_SMA_PERIOD = "sma_period"
CONF_SCAN_INTERVAL = "scan_interval"
CONF_NOTIFICATION_ENABLED = "notification_enabled"
CONF_NOTIFICATION_TIME = "notification_time"
CONF_NOTIFICATION_SERVICE = "notification_service"

DEFAULT_SMA_PERIOD = 200
DEFAULT_SCAN_INTERVAL = 60  # minutes
DEFAULT_NOTIFICATION_TIME = dt_time(22, 0)
DEFAULT_NOTIFICATION_SERVICE = "notify.pushover"

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
