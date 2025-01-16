"""Config flow for integration."""

from __future__ import annotations

# from collections.abc import Mapping
from datetime import timedelta
import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import (
    CONF_MONITORED_CONDITIONS,
    CONF_NAME,
    CONF_SCAN_INTERVAL,
    CONF_URL,
)
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import selector
import homeassistant.helpers.config_validation as cv

from .const import (
    CONF_BUTTONENABLED,
    CONF_BUTTONNAME,
    CONF_CERTPATH,
    CONF_CONTAINERS,
    CONF_CONTAINERS_EXCLUDE,
    CONF_MEMORYCHANGE,
    CONF_PRECISION_CPU,
    CONF_PRECISION_MEMORY_MB,
    CONF_PRECISION_MEMORY_PERCENTAGE,
    CONF_PRECISION_NETWORK_KB,
    CONF_PRECISION_NETWORK_MB,
    CONF_PREFIX,
    CONF_RENAME,
    CONF_RENAME_ENITITY,
    CONF_RETRY,
    CONF_SENSORNAME,
    CONF_SWITCHENABLED,
    CONF_SWITCHNAME,
    DEFAULT_BUTTONNAME,
    DEFAULT_NAME,
    DEFAULT_RETRY,
    DEFAULT_SENSORNAME,
    DEFAULT_SWITCHNAME,
    DOMAIN,
    MONITORED_CONDITIONS_LIST,
    PRECISION,
)
from .helpers import DockerAPI

_LOGGER = logging.getLogger(__name__)

# PLACEHOLDERS = {
#     CONF_URL: "URL",
# }


class DockerConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Docker config flow."""

    VERSION = 1
    data = None
    options = None
    _reauth_entry: config_entries.ConfigEntry | None = None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle user step."""
        errors = {}
        # defaults = {
        #     CONF_URL: "",
        # }

        if user_input is not None:
            await self.async_set_unique_id(user_input[CONF_URL])

            if not self._reauth_entry:
                self._abort_if_unique_id_configured()

            self.data = user_input
            self.data[CONF_SCAN_INTERVAL] = timedelta(
                seconds=user_input[CONF_SCAN_INTERVAL]
            )

            try:
                docker_api = DockerAPI(self.hass, user_input)
                if not await docker_api.init():
                    errors["base"] = "invalid_connection"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unhandled exception in user step")
                errors["base"] = "unknown"

            if not errors:
                # if self._reauth_entry:
                #     self.hass.config_entries.async_update_entry(
                #         self._reauth_entry, data=self._reauth_entry.data | user_input
                #     )
                #     await self.hass.config_entries.async_reload(
                #         self._reauth_entry.entry_id
                #     )
                #     return self.async_abort(reason="reauth_successful")

                return self.async_create_entry(title="Docker", data=self.data)

        # elif self._reauth_entry:
        #     for key in defaults:
        #         defaults[key] = self._reauth_entry.data.get(key)

        user_schema = vol.Schema(
            {
                vol.Required(CONF_NAME, default=DEFAULT_NAME): str,
                vol.Optional(CONF_PREFIX, default=""): str,
                vol.Optional(CONF_URL, default=None): str,
                vol.Required(CONF_SCAN_INTERVAL, default=10): int,
                vol.Optional(
                    CONF_MONITORED_CONDITIONS, default=[]
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=MONITORED_CONDITIONS_LIST,
                        multiple=True,
                    ),
                ),
                # vol.Optional(CONF_CONTAINERS, default=[]): cv.ensure_list,
                # vol.Optional(CONF_CONTAINERS_EXCLUDE, default=[]): cv.ensure_list,
                # vol.Optional(CONF_RENAME, default={}): dict,
                # vol.Optional(CONF_RENAME_ENITITY, default=False): cv.boolean,
                vol.Optional(CONF_SENSORNAME, default=DEFAULT_SENSORNAME): str,
                vol.Optional(CONF_SWITCHENABLED, default=True): bool,
                vol.Optional(CONF_BUTTONENABLED, default=False): bool,
                vol.Optional(CONF_SWITCHNAME, default=DEFAULT_SWITCHNAME): str,
                vol.Optional(CONF_BUTTONNAME, default=DEFAULT_BUTTONNAME): str,
                vol.Optional(CONF_CERTPATH, default=""): str,
                vol.Optional(CONF_RETRY, default=DEFAULT_RETRY): int,
                vol.Optional(CONF_MEMORYCHANGE, default=100): int,
                vol.Optional(CONF_PRECISION_CPU, default=PRECISION): int,
                vol.Optional(CONF_PRECISION_MEMORY_MB, default=PRECISION): int,
                vol.Optional(CONF_PRECISION_MEMORY_PERCENTAGE, default=PRECISION): int,
                vol.Optional(CONF_PRECISION_NETWORK_KB, default=PRECISION): int,
                vol.Optional(CONF_PRECISION_NETWORK_MB, default=PRECISION): int,
            }
        )

        return self.async_show_form(
            step_id="user",
            # data_schema=DOCKER_SCHEMA,
            data_schema=user_schema,
            # description_placeholders=PLACEHOLDERS,
            errors=errors,
        )

    # async def async_step_import(self, import_data) -> FlowResult:
    #     """Import config from configuration.yaml."""
    #     return await self.async_step_user(import_data)

    # async def async_step_reauth(self, user_input: Mapping[str, Any]) -> FlowResult:
    #     """Perform reauth upon an API authentication error."""
    #     self._reauth_entry = self.hass.config_entries.async_get_entry(
    #         self.context["entry_id"]
    #     )
    #     return await self.async_step_user()
