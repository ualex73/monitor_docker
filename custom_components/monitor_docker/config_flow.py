"""Config flow for integration."""

from __future__ import annotations

from collections.abc import Mapping
import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_API_KEY
from homeassistant.data_entry_flow import FlowResult
import homeassistant.helpers.config_validation as cv

from . import DOMAIN, InvalidAuth
from .helpers import DockerAPI, DockerContainerAPI

_LOGGER = logging.getLogger(__name__)

# PLACEHOLDERS = {
#     CONF_API_KEY: "API key",
# }


class DockerConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Docker config flow."""

    VERSION = 1
    _reauth_entry: config_entries.ConfigEntry | None = None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle user step."""
        errors = {}
        defaults = {
            CONF_API_KEY: "",
        }

        if user_input is not None:
            await self.async_set_unique_id(user_input[CONF_API_KEY])

            if not self._reauth_entry:
                self._abort_if_unique_id_configured()

            try:
                await self.is_valid(user_input)
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unhandled exception in user step")
                errors["base"] = "unknown"
            if not errors:
                if self._reauth_entry:
                    self.hass.config_entries.async_update_entry(
                        self._reauth_entry, data=self._reauth_entry.data | user_input
                    )
                    await self.hass.config_entries.async_reload(
                        self._reauth_entry.entry_id
                    )
                    return self.async_abort(reason="reauth_successful")

                return self.async_create_entry(title="Docker", data=user_input)
        elif self._reauth_entry:
            for key in defaults:
                defaults[key] = self._reauth_entry.data.get(key)

        user_schema = vol.Schema(
            {
                vol.Required(CONF_API_KEY, default=None): cv.string,
            }
        )
        return self.async_show_form(
            step_id="user",
            data_schema=user_schema,
            description_placeholders=PLACEHOLDERS,
            errors=errors,
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle user reconfiguration step."""
        errors = {}

        config_entry = self.hass.config_entries.async_get_entry(
            self.context["entry_id"]
        )
        if config_entry is None:
            return self.async_abort(reason="reconfigure_failed")

        if user_input is not None:
            try:
                await self.is_valid(user_input)
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unhandled exception in user step")
                errors["base"] = "unknown"
            if not errors:
                return self.async_update_reload_and_abort(
                    config_entry,
                    data=user_input,
                )

        default_api_key = config_entry.data.get(CONF_API_KEY) or None
        user_schema = vol.Schema(
            {
                vol.Required(CONF_API_KEY, default=default_api_key): cv.string,
            }
        )
        return self.async_show_form(
            step_id="reconfigure",
            data_schema=user_schema,
            description_placeholders=PLACEHOLDERS,
            errors=errors,
        )

    async def async_step_import(self, import_data) -> FlowResult:
        """Import config from configuration.yaml."""
        return await self.async_step_user(import_data)

    async def async_step_reauth(self, user_input: Mapping[str, Any]) -> FlowResult:
        """Perform reauth upon an API authentication error."""
        self._reauth_entry = self.hass.config_entries.async_get_entry(
            self.context["entry_id"]
        )
        return await self.async_step_user()

    # async def is_valid(self, user_input):
    #     """Check for user input errors."""
    #     docker_api = DockerApi(user_input[CONF_API_KEY])
    #     if not await docker_api.test():
    #         raise InvalidAuth