"""Constants for the Aurion Planning integration."""

from datetime import timedelta

DOMAIN = "aurion_planning"

# Mauria API Configuration
MAURIA_API_URL = "https://mauria-api.fly.dev"
LOGIN_ENDPOINT = "/aurion/login"
PLANNING_ENDPOINT = "/aurion/planning"
ABSENCES_ENDPOINT = "/aurion/absences"

# Form fields
CONF_EMAIL = "email"
CONF_PASSWORD = "password"

# Default settings
DEFAULT_SCAN_INTERVAL = timedelta(minutes=30)
DEFAULT_PLANNING_RANGE_DAYS = 60  # Fetch planning for the next 60 days

# Attributes
ATTR_EVENTS = "events"
ATTR_ABSENCES = "absences"
ATTR_LAST_UPDATED = "last_updated"
ATTR_TOTAL_ABSENCES = "total_absences"

# Error messages
ERROR_AUTH_FAILED = "auth_failed"
ERROR_CONNECTION = "connection_error"
ERROR_PARSING = "parsing_error"

# Calendar
CALENDAR_NAME = "Aurion Calendar"
