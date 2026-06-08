"""Config flow for Mauria Calendar integration."""

from typing import Any, Dict, Optional
import logging

from homeassistant import config_entries
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError
import homeassistant.helpers.config_entry_oauth2_flow as oauth2

from aiohttp import ClientSession, ClientError
from .const import (
    DOMAIN,
    DEFAULT_API_URL,
    CONF_USERNAME,
    CONF_PASSWORD,
    ERROR_AUTH_FAILED,
    ERROR_CONNECTION,
)

_LOGGER = logging.getLogger(__name__)


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Mauria Calendar."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_CLOUD_POLL

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Get the options flow for this handler."""
        return OptionsFlowHandler(config_entry)

    async def async_step_user(
        self, user_input: Optional[Dict[str, Any]] = None
    ) -> FlowResult:
        """Handle the initial step (UI form)."""
        errors: Dict[str, str] = {}

        if user_input is not None:
            # Validate the user input
            try:
                await self._validate_auth(
                    user_input[CONF_USERNAME],
                    user_input[CONF_PASSWORD],
                )
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except Exception as e:
                _LOGGER.error("Unexpected error: %s", e)
                errors["base"] = "unknown"
            else:
                # Create the config entry
                return self.async_create_entry(
                    title=user_input[CONF_USERNAME],
                    data=user_input,
                )

        # Show the form with the current errors
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_USERNAME): str,
                    vol.Required(CONF_PASSWORD): str,
                }
            ),
            errors=errors,
        )

    async def _validate_auth(
        self, username: str, password: str
    ) -> None:
        """Validate the user credentials by connecting to the API."""
        session = ClientSession()
        try:
            # Example: Try to authenticate with the API
            # Replace this with the actual authentication logic for Mauria API
            auth_url = f"{DEFAULT_API_URL}/auth/login"
            auth_data = {
                "username": username,
                "password": password,
            }
            
            async with session.post(auth_url, json=auth_data) as response:
                if response.status != 200:
                    raise InvalidAuth
                
                # If authentication succeeds, try to fetch the calendar
                calendar_url = f"{DEFAULT_API_URL}/calendar"
                headers = {
                    "Authorization": f"Bearer {await response.json()}",
                }
                async with session.get(calendar_url, headers=headers) as calendar_response:
                    if calendar_response.status != 200:
                        raise CannotConnect
        except ClientError as e:
            _LOGGER.error("Connection error: %s", e)
            raise CannotConnect
        finally:
            await session.close()


class OptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options flow for Mauria Calendar."""

    def __init__(self, config_entry: config_entries.ConfigEntry):
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: Optional[Dict[str, Any]] = None
    ) -> FlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional("scan_interval", default=30): int,
                }
            ),
        )


class InvalidAuth(HomeAssistantError):
    """Error to indicate invalid authentication."""


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


# Import vol after defining the classes to avoid circular imports
import voluptuous as vol
