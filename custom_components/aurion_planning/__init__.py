"""The Aurion Planning integration."""

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from aiohttp import ClientSession

from .const import DOMAIN

PLATFORMS = [Platform.SENSOR, Platform.CALENDAR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Aurion Planning from a config entry."""
    hass.data.setdefault(DOMAIN, {})
    
    # Create a shared session for all entities
    session = ClientSession()
    hass.data[DOMAIN][entry.entry_id] = {
        "session": session,
        "entry_data": entry.data,
    }
    
    # Forward the setup to the sensor and calendar platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    # Close the shared session
    if DOMAIN in hass.data and entry.entry_id in hass.data[DOMAIN]:
        session = hass.data[DOMAIN][entry.entry_id].get("session")
        if session:
            await session.close()
        hass.data[DOMAIN].pop(entry.entry_id)
    
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    return unload_ok
