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
    LOGIN_ENDPOINT,
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
    # Get the shared session from hass.data
    session = hass.data[DOMAIN][entry.entry_id]["session"]
    email = entry.data[CONF_EMAIL]
    password = entry.data[CONF_PASSWORD]
    planning_range_days = entry.options.get("planning_range_days", DEFAULT_PLANNING_RANGE_DAYS)

    # Initialize coordinators with the shared session
    planning_coordinator = AurionPlanningCoordinator(hass, session, email, password, planning_range_days)
    absences_coordinator = AurionAbsencesCoordinator(hass, session, email, password)
    
    # Fetch initial data
    await planning_coordinator.async_config_entry_first_refresh()
    await absences_coordinator.async_config_entry_first_refresh()

    # Add sensors
    async_add_entities([
        AurionPlanningSensor(planning_coordinator, entry),
        AurionAbsencesSensor(absences_coordinator, entry),
    ])


class AurionAPIClient:
    """Client for interacting with the Mauria API."""

    def __init__(self, session: ClientSession, email: str, password: str) -> None:
        """Initialize the API client."""
        self._session = session
        self._email = email
        self._password = password
        self._is_logged_in = False

    async def login(self) -> bool:
        """Login to Mauria API and return success status."""
        try:
            login_url = f"{MAURIA_API_URL}{LOGIN_ENDPOINT}"
            login_data = {
                "email": self._email,
                "password": self._password,
            }

            _LOGGER.debug("Attempting login to Mauria API with email: %s", self._email)
            async with self._session.post(login_url, json=login_data) as response:
                _LOGGER.debug("Login response status: %s", response.status)
                if response.status != 200:
                    _LOGGER.error("Login failed with status %s", response.status)
                    return False

                response_data = await response.json()
                _LOGGER.debug("Login response data: %s", response_data)
                if not response_data.get("success", False):
                    _LOGGER.error("Login failed: %s", response_data.get("error", "Unknown error"))
                    return False

                self._is_logged_in = True
                _LOGGER.debug("Login successful")
                return True

        except ClientError as e:
            _LOGGER.error("Connection error during login: %s", e)
            return False

    async def fetch_planning(self, start_timestamp: int, end_timestamp: int) -> Optional[List[Dict[str, Any]]]:
        """Fetch planning data from Mauria API."""
        if not self._is_logged_in:
            if not await self.login():
                return None
        
        try:
            planning_url = f"{MAURIA_API_URL}{PLANNING_ENDPOINT}"
            request_data = {
                "email": self._email,
                "password": self._password,
                "startTimestamp": start_timestamp,
                "endTimestamp": end_timestamp,
            }

            _LOGGER.debug("Fetching planning from %s to %s", start_timestamp, end_timestamp)
            _LOGGER.debug("Request data: %s", request_data)
            async with self._session.post(planning_url, json=request_data) as response:
                _LOGGER.debug("Planning response status: %s", response.status)
                if response.status != 200:
                    response_text = await response.text()
                    _LOGGER.error("Planning request failed with status %s, response: %s", response.status, response_text)
                    return None

                response_data = await response.json()
                _LOGGER.debug("Planning response data: %s", response_data)
                if not response_data.get("success", False):
                    _LOGGER.error("Planning request failed: %s", response_data.get("error", "Unknown error"))
                    return None

                return response_data.get("data", [])

        except ClientError as e:
            _LOGGER.error("Connection error during planning fetch: %s", e)
            return None

    async def fetch_absences(self) -> Optional[List[Dict[str, Any]]]:
        """Fetch absences data from Mauria API."""
        if not self._is_logged_in:
            if not await self.login():
                return None
        
        try:
            absences_url = f"{MAURIA_API_URL}{ABSENCES_ENDPOINT}"
            request_data = {
                "email": self._email,
                "password": self._password,
            }

            _LOGGER.debug("Fetching absences")
            _LOGGER.debug("Request data: %s", request_data)
            async with self._session.post(absences_url, json=request_data) as response:
                _LOGGER.debug("Absences response status: %s", response.status)
                if response.status != 200:
                    response_text = await response.text()
                    _LOGGER.error("Absences request failed with status %s, response: %s", response.status, response_text)
                    return None

                response_data = await response.json()
                _LOGGER.debug("Absences response data: %s", response_data)
                if not response_data.get("success", False):
                    _LOGGER.error("Absences request failed: %s", response_data.get("error", "Unknown error"))
                    return None

                return response_data.get("data", [])

        except ClientError as e:
            _LOGGER.error("Connection error during absences fetch: %s", e)
            return None


class AurionPlanningCoordinator(DataUpdateCoordinator):
    """Coordinator to fetch planning data from Mauria API."""

    def __init__(
        self, hass: HomeAssistant, session: ClientSession, email: str, password: str, planning_range_days: int
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_planning",
            update_interval=DEFAULT_SCAN_INTERVAL,
        )
        self._session = session
        self._email = email
        self._password = password
        self._planning_range_days = planning_range_days
        self._client = AurionAPIClient(session, email, password)
        self._events: List[Dict[str, Any]] = []
        self._last_updated: Optional[datetime] = None

    async def _async_update_data(self) -> Dict[str, Any]:
        """Fetch data from Mauria API."""
        try:
            # Calculate date range
            now = datetime.now()
            start_timestamp = int(now.timestamp() * 1000)
            end_timestamp = int((now + timedelta(days=self._planning_range_days)).timestamp() * 1000)

            _LOGGER.debug("Updating planning data, range: %s to %s", start_timestamp, end_timestamp)

            # Fetch planning data
            self._events = await self._client.fetch_planning(start_timestamp, end_timestamp)
            if self._events is None:
                raise UpdateFailed("Failed to fetch planning data")

            self._last_updated = datetime.now()

            return {
                ATTR_EVENTS: self._events,
                ATTR_LAST_UPDATED: self._last_updated,
            }

        except Exception as e:
            _LOGGER.error("Error fetching planning: %s", e)
            raise UpdateFailed(f"Error fetching planning: {e}")

    async def async_shutdown(self) -> None:
        """Close the client on shutdown."""
        pass  # Session is managed by the integration


class AurionAbsencesCoordinator(DataUpdateCoordinator):
    """Coordinator to fetch absences data from Mauria API."""

    def __init__(
        self, hass: HomeAssistant, session: ClientSession, email: str, password: str
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_absences",
            update_interval=DEFAULT_SCAN_INTERVAL,
        )
        self._session = session
        self._email = email
        self._password = password
        self._client = AurionAPIClient(session, email, password)
        self._absences: List[Dict[str, Any]] = []
        self._last_updated: Optional[datetime] = None

    async def _async_update_data(self) -> Dict[str, Any]:
        """Fetch absences data from Mauria API."""
        try:
            _LOGGER.debug("Updating absences data")

            # Fetch absences data
            self._absences = await self._client.fetch_absences()
            if self._absences is None:
                raise UpdateFailed("Failed to fetch absences data")

            self._last_updated = datetime.now()

            return {
                ATTR_ABSENCES: self._absences,
                ATTR_LAST_UPDATED: self._last_updated,
                ATTR_TOTAL_ABSENCES: len(self._absences),
            }

        except Exception as e:
            _LOGGER.error("Error fetching absences: %s", e)
            raise UpdateFailed(f"Error fetching absences: {e}")

    async def async_shutdown(self) -> None:
        """Close the client on shutdown."""
        pass  # Session is managed by the integration


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
