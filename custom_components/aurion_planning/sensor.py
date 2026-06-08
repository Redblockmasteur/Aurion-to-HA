"""Sensor platform for Aurion Planning integration."""

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
    CONF_EMAIL,
    CONF_PASSWORD,
    MAURIA_API_URL,
    PLANNING_ENDPOINT,
    ABSENCES_ENDPOINT,
    ATTR_EVENTS,
    ATTR_ABSENCES,
    ATTR_LAST_UPDATED,
    ATTR_TOTAL_ABSENCES,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_PLANNING_RANGE_DAYS,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Aurion Planning and Absences sensors."""
    email = entry.data[CONF_EMAIL]
    password = entry.data[CONF_PASSWORD]
    planning_range_days = entry.options.get("planning_range_days", DEFAULT_PLANNING_RANGE_DAYS)

    # Initialize coordinators
    planning_coordinator = AurionPlanningCoordinator(hass, email, password, planning_range_days)
    absences_coordinator = AurionAbsencesCoordinator(hass, email, password)
    
    # Fetch initial data
    await planning_coordinator.async_config_entry_first_refresh()
    await absences_coordinator.async_config_entry_first_refresh()

    # Add sensors
    async_add_entities([
        AurionPlanningSensor(planning_coordinator, entry),
        AurionAbsencesSensor(absences_coordinator, entry),
    ])


class AurionPlanningCoordinator(DataUpdateCoordinator):
    """Coordinator to fetch planning data from Mauria API."""

    def __init__(
        self, hass: HomeAssistant, email: str, password: str, planning_range_days: int
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_planning",
            update_interval=DEFAULT_SCAN_INTERVAL,
        )
        self._email = email
        self._password = password
        self._planning_range_days = planning_range_days
        self._session: Optional[ClientSession] = None
        self._events: List[Dict[str, Any]] = []
        self._last_updated: Optional[datetime] = None

    async def _async_update_data(self) -> Dict[str, Any]:
        """Fetch planning data from Mauria API."""
        self._session = ClientSession()
        try:
            # Calculate date range
            now = datetime.now()
            start_timestamp = int(now.timestamp() * 1000)  # Current time in milliseconds
            end_timestamp = int((now + timedelta(days=self._planning_range_days)).timestamp() * 1000)

            # Prepare the request
            planning_url = f"{MAURIA_API_URL}{PLANNING_ENDPOINT}"
            request_data = {
                "email": self._email,
                "password": self._password,
                "startTimestamp": start_timestamp,
                "endTimestamp": end_timestamp,
            }

            _LOGGER.debug("Fetching planning from Mauria API: %s", planning_url)
            async with self._session.post(planning_url, json=request_data) as response:
                if response.status != 200:
                    raise UpdateFailed(f"API request failed with status {response.status}")

                response_data = await response.json()
                
                if not response_data.get("success", False):
                    error = response_data.get("error", "Unknown error")
                    raise UpdateFailed(f"API error: {error}")

                # Extract events
                self._events = response_data.get("data", [])
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
        finally:
            if self._session:
                await self._session.close()
                self._session = None

    async def async_shutdown(self) -> None:
        """Close the session on shutdown."""
        if self._session:
            await self._session.close()
            self._session = None


class AurionAbsencesCoordinator(DataUpdateCoordinator):
    """Coordinator to fetch absences data from Mauria API."""

    def __init__(
        self, hass: HomeAssistant, email: str, password: str
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_absences",
            update_interval=DEFAULT_SCAN_INTERVAL,
        )
        self._email = email
        self._password = password
        self._session: Optional[ClientSession] = None
        self._absences: List[Dict[str, Any]] = []
        self._last_updated: Optional[datetime] = None

    async def _async_update_data(self) -> Dict[str, Any]:
        """Fetch absences data from Mauria API."""
        self._session = ClientSession()
        try:
            # Prepare the request
            absences_url = f"{MAURIA_API_URL}{ABSENCES_ENDPOINT}"
            request_data = {
                "email": self._email,
                "password": self._password,
            }

            _LOGGER.debug("Fetching absences from Mauria API: %s", absences_url)
            async with self._session.post(absences_url, json=request_data) as response:
                if response.status != 200:
                    raise UpdateFailed(f"API request failed with status {response.status}")

                response_data = await response.json()
                
                if not response_data.get("success", False):
                    error = response_data.get("error", "Unknown error")
                    raise UpdateFailed(f"API error: {error}")

                # Extract absences
                self._absences = response_data.get("data", [])
                self._last_updated = datetime.now()

                return {
                    ATTR_ABSENCES: self._absences,
                    ATTR_LAST_UPDATED: self._last_updated,
                    ATTR_TOTAL_ABSENCES: len(self._absences),
                }

        except ClientError as e:
            _LOGGER.error("Connection error: %s", e)
            raise UpdateFailed(f"Connection error: {e}")
        except Exception as e:
            _LOGGER.error("Unexpected error: %s", e)
            raise UpdateFailed(f"Unexpected error: {e}")
        finally:
            if self._session:
                await self._session.close()
                self._session = None

    async def async_shutdown(self) -> None:
        """Close the session on shutdown."""
        if self._session:
            await self._session.close()
            self._session = None


class AurionPlanningSensor(CoordinatorEntity, SensorEntity):
    """Representation of an Aurion Planning sensor."""

    def __init__(
        self, coordinator: AurionPlanningCoordinator, entry: ConfigEntry
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._entry = entry
        self._attr_name = f"Aurion Planning - {entry.data[CONF_EMAIL]}"
        self._attr_unique_id = f"{DOMAIN}_planning_{entry.entry_id}"
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


class AurionAbsencesSensor(CoordinatorEntity, SensorEntity):
    """Representation of an Aurion Absences sensor."""

    def __init__(
        self, coordinator: AurionAbsencesCoordinator, entry: ConfigEntry
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._entry = entry
        self._attr_name = f"Aurion Absences - {entry.data[CONF_EMAIL]}"
        self._attr_unique_id = f"{DOMAIN}_absences_{entry.entry_id}"
        self._attr_device_class = SensorDeviceClass.NUMBER
        self._attr_state_class = SensorStateClass.TOTAL
        self._attr_native_unit_of_measurement = "absences"
        self._attr_extra_state_attributes = {
            ATTR_ATTRIBUTION: "Data provided by Mauria API",
        }

    @property
    def native_value(self) -> Optional[int]:
        """Return the total number of absences."""
        if self.coordinator.data and ATTR_TOTAL_ABSENCES in self.coordinator.data:
            return self.coordinator.data[ATTR_TOTAL_ABSENCES]
        return None

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return the state attributes."""
        attributes = super().extra_state_attributes or {}
        if self.coordinator.data:
            attributes[ATTR_ABSENCES] = self.coordinator.data.get(ATTR_ABSENCES, [])
            attributes[ATTR_LAST_UPDATED] = self.coordinator.data.get(
                ATTR_LAST_UPDATED
            )
            attributes[ATTR_TOTAL_ABSENCES] = self.coordinator.data.get(
                ATTR_TOTAL_ABSENCES
            )
        return attributes

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self.async_write_ha_state()
