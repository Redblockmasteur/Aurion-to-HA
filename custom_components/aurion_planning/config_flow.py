"""Config flow for Aurion Planning integration."""

from typing import Any, Dict, Optional
import logging

from homeassistant import config_entries
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError

import voluptuous as vol

from .const import (
    DOMAIN,
    CONF_EMAIL,
    CONF_PASSWORD,
    MAURIA_API_URL,
    LOGIN_ENDPOINT,
    ERROR_AUTH_FAILED,
    ERROR_CONNECTION,
)
from aiohttp import ClientSession, ClientError

_LOGGER = logging.getLogger(__name__)


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Aurion Planning."""

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
                    user_input[CONF_EMAIL],
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
                    title=user_input[CONF_EMAIL],
                    data=user_input,
                )

        # Show the form with the current errors
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_EMAIL): str,
                    vol.Required(CONF_PASSWORD): str,
                }
            ),
            errors=errors,
        )

    async def _validate_auth(self, email: str, password: str) -> None:
        """Validate the user credentials by connecting to Mauria API."""
        session = ClientSession()
        try:
            # Try to login via Mauria API
            login_url = f"{MAURIA_API_URL}{LOGIN_ENDPOINT}"
            login_data = {
                "email": email,
                "password": password,
            }

            async with session.post(login_url, json=login_data) as response:
                if response.status != 200:
                    raise CannotConnect

                login_response = await response.json()
                if not login_response.get("success", False):
                    raise InvalidAuth

        except ClientError as e:
            _LOGGER.error("Connection error: %s", e)
            raise CannotConnect
        finally:
            await session.close()


class OptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options flow for Aurion Planning."""

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
                    vol.Optional("planning_range_days", default=60): int,
                }
            ),
        )


class InvalidAuth(HomeAssistantError):
    """Error to indicate invalid authentication."""


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""
