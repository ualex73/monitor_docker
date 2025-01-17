"""Config flow for integration."""

from __future__ import annotations

# from collections.abc import Mapping
from datetime import timedelta
import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries, data_entry_flow
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
    CONF_MONITORED_CONTAINER_CONDITIONS,
    CONF_MONITORED_DOCKER_CONDITIONS,
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
    CONTAINER_MONITOR_LIST,
    CONTAINER_PRE_SELECTION,
    DEFAULT_BUTTONNAME,
    DEFAULT_NAME,
    DEFAULT_RETRY,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_SENSORNAME,
    DEFAULT_SWITCHNAME,
    DOCKER_MONITOR_LIST,
    DOCKER_PRE_SELECTION,
    DOMAIN,
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
    data = {
        # User
        CONF_NAME: DEFAULT_NAME,
        CONF_PREFIX: "",
        CONF_URL: "",
        CONF_SCAN_INTERVAL: DEFAULT_SCAN_INTERVAL,
        CONF_CERTPATH: "",
        CONF_RETRY: DEFAULT_RETRY,
        # Containers
        CONF_CONTAINERS: [],
        CONF_CONTAINERS_EXCLUDE: [],
        CONF_RENAME: {},
        CONF_RENAME_ENITITY: False,
        # Conditions
        CONF_MONITORED_CONDITIONS: [],
        CONF_SENSORNAME: DEFAULT_SENSORNAME,
        CONF_SWITCHENABLED: True,
        CONF_SWITCHNAME: DEFAULT_SWITCHNAME,
        CONF_BUTTONENABLED: False,
        CONF_BUTTONNAME: DEFAULT_BUTTONNAME,
        CONF_MEMORYCHANGE: 100,
        CONF_PRECISION_CPU: PRECISION,
        CONF_PRECISION_MEMORY_MB: PRECISION,
        CONF_PRECISION_MEMORY_PERCENTAGE: PRECISION,
        CONF_PRECISION_NETWORK_KB: PRECISION,
        CONF_PRECISION_NETWORK_MB: PRECISION,
    }
    options = None
    _docker_api = None
    _reauth_entry: config_entries.ConfigEntry | None = None
    _docker_conditions = DOCKER_PRE_SELECTION
    _container_conditions = CONTAINER_PRE_SELECTION

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle user step."""
        errors = {}

        if user_input is not None:
            self.data.update(user_input)

            if (
                DOMAIN in self.hass.data
                and user_input[CONF_NAME] in self.hass.data[DOMAIN]
            ):
                errors[CONF_NAME] = "name_exists"
                # raise data_entry_flow.AbortFlow("already_configured")

            await self.async_set_unique_id(user_input[CONF_NAME])

            if not self._reauth_entry:
                self._abort_if_unique_id_configured()

            # Convert some user_input data as preparation to calling API
            # user_input[CONF_SCAN_INTERVAL] = timedelta(
            #     seconds=user_input[CONF_SCAN_INTERVAL]
            # )
            if user_input[CONF_URL] == "":
                user_input[CONF_URL] = None
            user_input[CONF_MEMORYCHANGE] = self.data[CONF_MEMORYCHANGE]

            try:
                self._docker_api = DockerAPI(self.hass, user_input)
                if not await self._docker_api.init():
                    errors["base"] = "invalid_connection"
            except Exception as e:  # pylint: disable=broad-except
                _LOGGER.exception("Unhandled exception in user step")
                errors["base"] = str(e)

            if not errors:
                self.data.update(user_input)
                # if self._reauth_entry:
                #     self.hass.config_entries.async_update_entry(
                #         self._reauth_entry, data=self._reauth_entry.data | user_input
                #     )
                #     await self.hass.config_entries.async_reload(
                #         self._reauth_entry.entry_id
                #     )
                #     return self.async_abort(reason="reauth_successful")
                return await self.async_step_containers()

        # elif self._reauth_entry:
        #     for key in defaults:
        #         defaults[key] = self._reauth_entry.data.get(key)

        user_schema = vol.Schema(
            {
                vol.Required(CONF_NAME, default=self.data[CONF_NAME]): str,
                vol.Optional(CONF_PREFIX, default=self.data[CONF_PREFIX]): str,
                vol.Optional(CONF_URL, default=self.data[CONF_URL]): str,
                vol.Required(
                    CONF_SCAN_INTERVAL, default=self.data[CONF_SCAN_INTERVAL]
                ): int,
                vol.Optional(CONF_CERTPATH, default=self.data[CONF_CERTPATH]): str,
                vol.Required(CONF_RETRY, default=self.data[CONF_RETRY]): int,
            }
        )

        return self.async_show_form(
            step_id="user",
            # data_schema=DOCKER_SCHEMA,
            data_schema=user_schema,
            # description_placeholders=PLACEHOLDERS,
            errors=errors,
        )

    async def async_step_containers(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle user step."""
        errors = {}

        if user_input is not None:
            self.data.update(user_input)
            if not errors:
                return await self.async_step_conditions()

        container_schema = vol.Schema(
            {
                vol.Optional(CONF_CONTAINERS, default=[]): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=list(self._docker_api.list_containers()),
                        multiple=True,
                    ),
                ),
                # vol.Required(CONF_CONTAINERS_EXCLUDE, default=[]): cv.ensure_list,
                # vol.Required(CONF_RENAME, default={}): dict,
                vol.Required(CONF_RENAME_ENITITY, default=False): bool,
            }
        )

        return self.async_show_form(
            step_id="containers",
            data_schema=container_schema,
            # description_placeholders=PLACEHOLDERS,
            errors=errors,
        )

    async def async_step_conditions(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle user step."""
        errors = {}

        if user_input is not None:
            self._docker_conditions = user_input.pop(CONF_MONITORED_DOCKER_CONDITIONS)
            self._container_conditions = user_input.pop(
                CONF_MONITORED_CONTAINER_CONDITIONS
            )
            self.data.update(user_input)

            if not errors:
                self.data[CONF_MONITORED_CONDITIONS] = (
                    self._docker_conditions + self._container_conditions
                )
                return self.async_create_entry(
                    title=self.data[CONF_NAME], data=self.data
                )

        conditions_schema = vol.Schema(
            {
                vol.Optional(
                    CONF_MONITORED_DOCKER_CONDITIONS, default=self._docker_conditions
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=list(DOCKER_MONITOR_LIST),
                        multiple=True,
                    ),
                ),
                vol.Optional(
                    CONF_MONITORED_CONTAINER_CONDITIONS,
                    default=self._container_conditions,
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=list(CONTAINER_MONITOR_LIST),
                        multiple=True,
                    ),
                ),
                vol.Required(CONF_SENSORNAME, default=DEFAULT_SENSORNAME): str,
                vol.Required(CONF_SWITCHENABLED, default=True): bool,
                vol.Required(CONF_SWITCHNAME, default=DEFAULT_SWITCHNAME): str,
                vol.Required(CONF_BUTTONENABLED, default=False): bool,
                vol.Required(CONF_BUTTONNAME, default=DEFAULT_BUTTONNAME): str,
                vol.Required(CONF_MEMORYCHANGE, default=100): int,
                vol.Required(CONF_PRECISION_CPU, default=PRECISION): int,
                vol.Required(CONF_PRECISION_MEMORY_MB, default=PRECISION): int,
                vol.Required(CONF_PRECISION_MEMORY_PERCENTAGE, default=PRECISION): int,
                vol.Required(CONF_PRECISION_NETWORK_KB, default=PRECISION): int,
                vol.Required(CONF_PRECISION_NETWORK_MB, default=PRECISION): int,
            }
        )

        return self.async_show_form(
            step_id="conditions",
            data_schema=conditions_schema,
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
