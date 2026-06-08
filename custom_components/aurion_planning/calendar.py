"""Calendar platform for Aurion Planning integration."""

from datetime import datetime, timedelta
import logging
from typing import Any, Dict, List, Optional

from homeassistant.components.calendar import (
    CalendarEntity,
    CalendarEvent,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_ATTRIBUTION
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
    UpdateFailed,
)
from homeassistant.util.dt import now

from aiohttp import ClientSession, ClientError

from .const import (
    DOMAIN,
    CONF_EMAIL,
    CONF_PASSWORD,
    MAURIA_API_URL,
    PLANNING_ENDPOINT,
    LOGIN_ENDPOINT,
    CALENDAR_NAME,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_PLANNING_RANGE_DAYS,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Aurion Calendar."""
    # Get the shared session from hass.data
    session = hass.data[DOMAIN][entry.entry_id]["session"]
    email = entry.data[CONF_EMAIL]
    password = entry.data[CONF_PASSWORD]
    planning_range_days = entry.options.get("planning_range_days", DEFAULT_PLANNING_RANGE_DAYS)

    # Initialize the coordinator
    coordinator = AurionCalendarCoordinator(hass, session, email, password, planning_range_days)
    await coordinator.async_config_entry_first_refresh()

    # Add the calendar entity
    async_add_entities([AurionCalendarEntity(coordinator, entry)])


class AurionCalendarCoordinator(DataUpdateCoordinator):
    """Coordinator to fetch calendar data from Mauria API."""

    def __init__(
        self, hass: HomeAssistant, session: ClientSession, email: str, password: str, planning_range_days: int
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_calendar",
            update_interval=DEFAULT_SCAN_INTERVAL,
        )
        self._session = session
        self._email = email
        self._password = password
        self._planning_range_days = planning_range_days
        self._events: List[Dict[str, Any]] = []
        self._last_updated: Optional[datetime] = None
        self._is_logged_in = False

    async def _async_update_data(self) -> Dict[str, Any]:
        """Fetch data from Mauria API."""
        try:
            # Login first
            if not self._is_logged_in:
                login_url = f"{MAURIA_API_URL}{LOGIN_ENDPOINT}"
                login_data = {
                    "email": self._email,
                    "password": self._password,
                }

                _LOGGER.debug("Calendar: Attempting login to Mauria API")
                async with self._session.post(login_url, json=login_data) as response:
                    _LOGGER.debug("Calendar: Login response status: %s", response.status)
                    if response.status != 200:
                        raise UpdateFailed(f"Login failed with status {response.status}")

                    response_data = await response.json()
                    _LOGGER.debug("Calendar: Login response data: %s", response_data)
                    if not response_data.get("success", False):
                        raise UpdateFailed(f"Login failed: {response_data.get('error', 'Unknown error')}")

                    self._is_logged_in = True

            # Calculate date range
            now_dt = now()
            start_timestamp = int(now_dt.timestamp() * 1000)
            end_timestamp = int((now_dt + timedelta(days=self._planning_range_days)).timestamp() * 1000)

            # Fetch planning data
            planning_url = f"{MAURIA_API_URL}{PLANNING_ENDPOINT}"
            request_data = {
                "email": self._email,
                "password": self._password,
                "startTimestamp": start_timestamp,
                "endTimestamp": end_timestamp,
            }

            _LOGGER.debug("Calendar: Fetching planning from %s to %s", start_timestamp, end_timestamp)
            async with self._session.post(planning_url, json=request_data) as response:
                _LOGGER.debug("Calendar: Planning response status: %s", response.status)
                if response.status != 200:
                    response_text = await response.text()
                    raise UpdateFailed(f"Planning request failed with status {response.status}, response: {response_text}")

                response_data = await response.json()
                _LOGGER.debug("Calendar: Planning response data: %s", response_data)
                if not response_data.get("success", False):
                    raise UpdateFailed(f"Planning request failed: {response_data.get('error', 'Unknown error')}")

                self._events = response_data.get("data", [])
                self._last_updated = now()

                return {
                    "events": self._events,
                    "last_updated": self._last_updated,
                }

        except ClientError as e:
            _LOGGER.error("Calendar: Connection error: %s", e)
            raise UpdateFailed(f"Connection error: {e}")
        except Exception as e:
            _LOGGER.error("Calendar: Unexpected error: %s", e)
            raise UpdateFailed(f"Unexpected error: {e}")

    async def async_shutdown(self) -> None:
        """Close the session on shutdown."""
        pass  # Session is managed by the integration

    @property
    def events(self) -> List[Dict[str, Any]]:
        """Return the list of events."""
        return self._events


class AurionCalendarEntity(CoordinatorEntity, CalendarEntity):
    """Representation of an Aurion Calendar."""

    def __init__(
        self, coordinator: AurionCalendarCoordinator, entry: ConfigEntry
    ) -> None:
        """Initialize the calendar entity."""
        super().__init__(coordinator)
        self._entry = entry
        self._attr_name = f"{CALENDAR_NAME} - {entry.data[CONF_EMAIL]}"
        self._attr_unique_id = f"{DOMAIN}_calendar_{entry.entry_id}"
        self._attr_extra_state_attributes = {
            ATTR_ATTRIBUTION: "Data provided by Mauria API",
        }

    async def async_get_events(
        self,
        hass: HomeAssistant,
        start_date: datetime,
        end_date: datetime,
    ) -> List[CalendarEvent]:
        """Return calendar events within a datetime range."""
        events: List[CalendarEvent] = []
        
        if not self.coordinator.data or "events" not in self.coordinator.data:
            return events

        # Convert events from Mauria API to CalendarEvent format
        for event_data in self.coordinator.data["events"]:
            try:
                # Parse start and end dates from the event
                start_str = event_data.get("start")
                end_str = event_data.get("end")
                
                if not start_str or not end_str:
                    continue

                # Parse ISO format dates (assuming they are in UTC or with timezone)
                try:
                    start = datetime.fromisoformat(start_str.replace("Z", "+00:00"))
                    end = datetime.fromisoformat(end_str.replace("Z", "+00:00"))
                except ValueError:
                    # Try parsing as timestamp in milliseconds
                    start = datetime.fromtimestamp(int(start_str) / 1000)
                    end = datetime.fromtimestamp(int(end_str) / 1000)
                
                # Ensure start and end are timezone-aware
                if start.tzinfo is None:
                    start = start.replace(tzinfo=end_date.tzinfo)
                if end.tzinfo is None:
                    end = end.replace(tzinfo=end_date.tzinfo)

                # Skip events outside the requested range
                if start >= end_date or end <= start_date:
                    continue

                # Create CalendarEvent
                event = CalendarEvent(
                    start=start,
                    end=end,
                    summary=event_data.get("title", "Unknown Event"),
                    description=event_data.get("className", ""),
                    location=event_data.get("location", ""),
                    uid=f"aurion_{event_data.get('id', 'unknown')}",
                )
                events.append(event)

            except (ValueError, TypeError, KeyError) as e:
                _LOGGER.error("Error parsing event %s: %s", event_data, e)
                continue

        # Sort events by start date
        events.sort(key=lambda x: x.start)
        return events

    async def async_update_event_listeners(self) -> None:
        """Notify all event listeners of new events."""
        await super().async_update_event_listeners()

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self.async_write_ha_state()
