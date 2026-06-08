"""Sensor platform for Mauria Calendar integration."""

from datetime import datetime, timedelta
import logging
from typing import Any, Dict, List, Optional

from homeassistant.components.sensor import (
    SensorEntity,
    SensorDeviceClass,
    SensorStateClass,
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

from aiohttp import ClientSession, ClientError
from .const import (
    DOMAIN,
    DEFAULT_API_URL,
    API_CALENDAR_ENDPOINT,
    CONF_USERNAME,
    CONF_PASSWORD,
    ATTR_EVENTS,
    ATTR_LAST_UPDATED,
    DEFAULT_SCAN_INTERVAL,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Mauria Calendar sensor."""
    username = entry.data[CONF_USERNAME]
    password = entry.data[CONF_PASSWORD]

    # Initialize the coordinator
    coordinator = MauriaCalendarCoordinator(hass, username, password)
    await coordinator.async_config_entry_first_refresh()

    # Add the sensor
    async_add_entities([MauriaCalendarSensor(coordinator, entry)])


class MauriaCalendarCoordinator(DataUpdateCoordinator):
    """Coordinator to fetch data from Mauria API."""

    def __init__(
        self, hass: HomeAssistant, username: str, password: str
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=DEFAULT_SCAN_INTERVAL,
        )
        self._username = username
        self._password = password
        self._session = ClientSession()
        self._events: List[Dict[str, Any]] = []
        self._last_updated: Optional[datetime] = None

    async def _async_update_data(self) -> Dict[str, Any]:
        """Fetch data from Mauria API."""
        try:
            # Step 1: Authenticate
            auth_url = f"{DEFAULT_API_URL}/auth/login"
            auth_data = {
                "username": self._username,
                "password": self._password,
            }

            async with self._session.post(auth_url, json=auth_data) as response:
                if response.status != 200:
                    raise UpdateFailed("Authentication failed")
                
                auth_response = await response.json()
                token = auth_response.get("token")
                if not token:
                    raise UpdateFailed("No token received")

            # Step 2: Fetch calendar data
            calendar_url = f"{DEFAULT_API_URL}{API_CALENDAR_ENDPOINT}"
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            }

            async with self._session.get(calendar_url, headers=headers) as response:
                if response.status != 200:
                    raise UpdateFailed(f"Failed to fetch calendar: {response.status}")
                
                calendar_data = await response.json()
                self._events = calendar_data.get("events", [])
                self._last_updated = datetime.now()

            return {
                ATTR_EVENTS: self._events,
                ATTR_LAST_UPDATED: self._last_updated,
            }

        except ClientError as e:
            _LOGGER.error("Connection error: %s", e)
            raise UpdateFailed(f"Connection error: {e}")
        except Exception as e:
            _LOGGER.error("Unexpected error: %s", e)
            raise UpdateFailed(f"Unexpected error: {e}")

    async def async_shutdown(self) -> None:
        """Close the session on shutdown."""
        await self._session.close()


class MauriaCalendarSensor(CoordinatorEntity, SensorEntity):
    """Representation of a Mauria Calendar sensor."""

    def __init__(
        self, coordinator: MauriaCalendarCoordinator, entry: ConfigEntry
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._entry = entry
        self._attr_name = f"Mauria Calendar - {entry.data[CONF_USERNAME]}"
        self._attr_unique_id = f"{DOMAIN}_{entry.entry_id}"
        self._attr_device_class = SensorDeviceClass.TIMESTAMP
        self._attr_native_value = None
        self._attr_extra_state_attributes = {
            ATTR_ATTRIBUTION: "Data provided by Mauria API",
        }

    @property
    def native_value(self) -> Optional[str]:
        """Return the state of the sensor."""
        if self.coordinator.data and ATTR_LAST_UPDATED in self.coordinator.data:
            last_updated = self.coordinator.data[ATTR_LAST_UPDATED]
            if last_updated:
                return last_updated.isoformat()
        return None

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return the state attributes."""
        attributes = super().extra_state_attributes or {}
        if self.coordinator.data:
            attributes[ATTR_EVENTS] = self.coordinator.data.get(ATTR_EVENTS, [])
            attributes[ATTR_LAST_UPDATED] = self.coordinator.data.get(
                ATTR_LAST_UPDATED
            )
        return attributes

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self.async_write_ha_state()
