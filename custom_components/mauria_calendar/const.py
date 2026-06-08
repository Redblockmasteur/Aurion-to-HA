"""Constants for the Mauria Calendar integration."""

from datetime import timedelta

DOMAIN = "mauria_calendar"

# API Configuration
DEFAULT_API_URL = "https://api.mauria.app/v2"
API_CALENDAR_ENDPOINT = "/calendar"

# Authentication
CONF_USERNAME = "username"
CONF_PASSWORD = "password"

# Default settings
DEFAULT_SCAN_INTERVAL = timedelta(minutes=30)

# Attributes
ATTR_EVENTS = "events"
ATTR_LAST_UPDATED = "last_updated"

# Error messages
ERROR_AUTH_FAILED = "auth_failed"
ERROR_CONNECTION = "connection_error"
