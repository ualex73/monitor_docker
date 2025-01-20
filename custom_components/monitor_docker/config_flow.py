"""Config flow for integration."""

from __future__ import annotations

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

from .const import (
    CONF_BUTTONENABLED,
    CONF_BUTTONNAME,
    CONF_CERTPATH,
    CONF_CONTAINERS,
    CONF_CONTAINERS_EXCLUDE,
    CONF_MEMORYCHANGE,
    CONF_MONITORED_CONTAINER_CONDITIONS,
    CONF_MONITORED_DOCKER_CONDITIONS,
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

CONF_RENAME_CONTAINERS = "rename_containers"


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
        CONF_CONTAINERS_EXCLUDE: [],  # Not relevant as all are selected
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
    _rename_containers = False

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

            await self.async_set_unique_id(user_input[CONF_NAME])

            if not self._reauth_entry:
                self._abort_if_unique_id_configured()

            # Convert some user_input data as preparation to calling API
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
            data_schema=user_schema,
            errors=errors,
        )

    async def async_step_reconfigure(self, user_input: dict[str, Any] | None = None):
        """Handle reconfigure step."""
        entry_id = self.context["entry_id"]
        config_entry = await self.hass.config_entries.async_get_entry(entry_id)
        self.hass.data[DOMAIN][entry[CONF_NAME]][API]
        hass.data[DOMAIN][entry[CONF_NAME]][API]

        return self.async_show_menu(
            step_id="reconfigure",
            menu_options=["containers", "conditions"],
            # description_placeholders={
            #     "model": "Example model",
            # }
        )

        if user_input is not None:
            # TODO: process user input
            self.async_set_unique_id(user_id)
            self._abort_if_unique_id_mismatch()
            return self.async_update_reload_and_abort(
                self._get_reconfigure_entry(),
                data_updates=data,
            )

        return await self.async_step_containers()

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=vol.Schema({vol.Required("input_parameter"): str}),
        )

    async def async_step_containers(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle user step."""
        errors = {}

        if user_input is not None:
            self._rename_containers = user_input.pop(CONF_RENAME_CONTAINERS)
            self.data.update(user_input)
            if not errors:
                if self._rename_containers:
                    return await self.async_step_containers_rename()
                if self.source == config_entries.SOURCE_RECONFIGURE:
                    return None
                return await self.async_step_conditions()

        container_schema = vol.Schema(
            {
                vol.Optional(
                    CONF_CONTAINERS, default=self.data[CONF_CONTAINERS]
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=list(self._docker_api.list_containers()),
                        multiple=True,
                    ),
                ),
                vol.Required(
                    CONF_RENAME_CONTAINERS, default=self._rename_containers
                ): bool,
            }
        )

        return self.async_show_form(
            step_id="containers",
            data_schema=container_schema,
            errors=errors,
        )

    async def async_step_containers_rename(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle user step."""
        errors = {}

        if user_input is not None:
            # self.data.update(user_input)
            self.data[CONF_RENAME_ENITITY] = user_input.pop(CONF_RENAME_ENITITY)
            for container in self.data[CONF_CONTAINERS]:
                self.data[CONF_RENAME][container] = name = user_input.pop(container)
                if name in [
                    v for k, v in self.data[CONF_RENAME].items() if k != container
                ]:
                    errors["base"] = "duplicate_names"
                    self.data[CONF_RENAME].pop(container)
            if not errors:
                if self.source == config_entries.SOURCE_RECONFIGURE:
                    return None
                return await self.async_step_conditions()

        container_schema = vol.Schema(
            {
                vol.Required(
                    CONF_RENAME_ENITITY, default=self.data[CONF_RENAME_ENITITY]
                ): bool
            }
        )
        for container in self.data[CONF_CONTAINERS]:
            container_schema = container_schema.extend(
                {
                    vol.Required(
                        container,
                        default=self.data[CONF_RENAME].get(container, container),
                    ): str
                }
            )

        return self.async_show_form(
            step_id="containers_rename",
            data_schema=container_schema,
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
                if self.source == config_entries.SOURCE_RECONFIGURE:
                    return None
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
                vol.Required(CONF_SENSORNAME, default=self.data[CONF_SENSORNAME]): str,
                vol.Required(
                    CONF_SWITCHENABLED, default=self.data[CONF_SWITCHENABLED]
                ): bool,
                vol.Required(CONF_SWITCHNAME, default=self.data[CONF_SWITCHNAME]): str,
                vol.Required(
                    CONF_BUTTONENABLED, default=self.data[CONF_BUTTONENABLED]
                ): bool,
                vol.Required(CONF_BUTTONNAME, default=self.data[CONF_BUTTONNAME]): str,
                vol.Required(
                    CONF_MEMORYCHANGE, default=self.data[CONF_MEMORYCHANGE]
                ): int,
                vol.Required(
                    CONF_PRECISION_CPU, default=self.data[CONF_PRECISION_CPU]
                ): int,
                vol.Required(
                    CONF_PRECISION_MEMORY_MB,
                    default=self.data[CONF_PRECISION_MEMORY_MB],
                ): int,
                vol.Required(
                    CONF_PRECISION_MEMORY_PERCENTAGE,
                    default=self.data[CONF_PRECISION_MEMORY_PERCENTAGE],
                ): int,
                vol.Required(
                    CONF_PRECISION_NETWORK_KB,
                    default=self.data[CONF_PRECISION_NETWORK_KB],
                ): int,
                vol.Required(
                    CONF_PRECISION_NETWORK_MB,
                    default=self.data[CONF_PRECISION_NETWORK_MB],
                ): int,
            }
        )

        return self.async_show_form(
            step_id="conditions",
            data_schema=conditions_schema,
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
