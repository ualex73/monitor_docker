"""Config flow for integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import (
    SOURCE_REAUTH,
    SOURCE_RECONFIGURE,
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    Mapping,
)
from homeassistant.const import (
    CONF_MONITORED_CONDITIONS,
    CONF_NAME,
    CONF_SCAN_INTERVAL,
    CONF_URL,
)
from homeassistant.helpers import issue_registry as ir, selector

from .const import (
    API,
    CONF_BUTTONENABLED,
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
    CONF_RETRY,
    CONF_SWITCHENABLED,
    CONTAINER_MONITOR_LIST,
    CONTAINER_PRE_SELECTION,
    DEFAULT_NAME,
    DEFAULT_RETRY,
    DEFAULT_SCAN_INTERVAL,
    DOCKER_MONITOR_LIST,
    DOCKER_PRE_SELECTION,
    DOMAIN,
    PRECISION,
)
from .helpers import DockerAPI

_LOGGER = logging.getLogger(__name__)


class DockerConfigFlow(ConfigFlow, domain=DOMAIN):
    """Docker config flow."""

    VERSION = 1
    MINOR_VERSION = 1
    data = {
        # User
        CONF_NAME: DEFAULT_NAME,
        CONF_URL: "",
        CONF_SCAN_INTERVAL: DEFAULT_SCAN_INTERVAL,
        CONF_CERTPATH: "",
        CONF_RETRY: DEFAULT_RETRY,
        # Containers
        CONF_CONTAINERS: [],
        CONF_CONTAINERS_EXCLUDE: [],  # Not relevant as all are selected
        # Conditions
        CONF_MONITORED_CONDITIONS: [],
        CONF_SWITCHENABLED: True,
        CONF_BUTTONENABLED: False,
        CONF_MEMORYCHANGE: 100,
        CONF_PRECISION_CPU: PRECISION,
        CONF_PRECISION_MEMORY_MB: PRECISION,
        CONF_PRECISION_MEMORY_PERCENTAGE: PRECISION,
        CONF_PRECISION_NETWORK_KB: PRECISION,
        CONF_PRECISION_NETWORK_MB: PRECISION,
    }
    options = None
    _docker_api = None
    _config_entry: ConfigEntry | None = None
    _docker_conditions = DOCKER_PRE_SELECTION
    _container_conditions = CONTAINER_PRE_SELECTION

    async def async_step_user(
        self, user_input: Mapping[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle user step."""
        errors = {}

        if user_input is not None:
            self.data.update(user_input)

            # Convert some user_input data as preparation to calling API
            if user_input[CONF_URL] == "":
                user_input[CONF_URL] = None
            user_input[CONF_MEMORYCHANGE] = self.data[CONF_MEMORYCHANGE]

            # Test connection to Docker
            try:
                self._docker_api = DockerAPI(self.hass, user_input)
                await self._docker_api.init()
                #errors["base"] = "invalid_connection"
            except Exception as e:  # pylint: disable=broad-except
                _LOGGER.exception("Unhandled exception in user step")
                errors["base"] = str(e)

            # Unless re-authorization, check and abort if name already exists
            if self.source != SOURCE_REAUTH:
                if (
                    DOMAIN in self.hass.data
                    and user_input[CONF_NAME] in self.hass.data[DOMAIN]
                ):
                    errors[CONF_NAME] = "name_exists"

                await self.async_set_unique_id(user_input[CONF_NAME])
                if not self._config_entry:
                    self._abort_if_unique_id_configured()

            if not errors:
                if self.source == SOURCE_REAUTH:
                    return self.async_update_reload_and_abort(
                        self._config_entry,
                        data=self.data,
                    )
                return await self.async_step_containers()

        user_schema = vol.Schema(
            {
                vol.Required(CONF_NAME, default=self.data[CONF_NAME]): str,
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

    async def async_step_reconfigure(
        self, user_input: Mapping[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle reconfigure step."""
        self._config_entry = self.hass.config_entries.async_get_entry(
            self.context["entry_id"]
        )
        if self._config_entry is None:
            return self.async_abort(reason="reconfigure_failed")
        self.data = {**self._config_entry.data}
        self._docker_api = self.hass.data[DOMAIN][self._config_entry.data[CONF_NAME]][
            API
        ]

        return self.async_show_menu(
            step_id="reconfigure",
            menu_options=["containers", "conditions"],
        )

    async def async_step_reauth(
        self, user_input: Mapping[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Perform reauth upon an API authentication error."""
        self._config_entry = self.hass.config_entries.async_get_entry(
            self.context["entry_id"]
        )
        return await self.async_step_user(user_input)

    async def async_step_containers(
        self, user_input: Mapping[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle user step."""
        errors = {}

        if user_input is not None:
            self.data.update(user_input)
            if self.source == SOURCE_RECONFIGURE:
                # self.async_set_unique_id(self.data[CONF_NAME])
                # self._abort_if_unique_id_mismatch()
                return self.async_update_reload_and_abort(
                    self._config_entry,
                    data=self.data,
                )
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
                )
            }
        )

        return self.async_show_form(
            step_id="containers",
            data_schema=container_schema,
            errors=errors,
        )

    async def async_step_conditions(
        self, user_input: Mapping[str, Any] | None = None
    ) -> ConfigFlowResult:
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
                if self.source == SOURCE_RECONFIGURE:
                    # self.async_set_unique_id(self.data[CONF_NAME])
                    # self._abort_if_unique_id_mismatch()
                    return self.async_update_reload_and_abort(
                        self._config_entry,
                        data=self.data,
                        reason="reconfigure_successful",
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
                vol.Required(
                    CONF_SWITCHENABLED, default=self.data[CONF_SWITCHENABLED]
                ): bool,
                vol.Required(
                    CONF_BUTTONENABLED, default=self.data[CONF_BUTTONENABLED]
                ): bool,
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

    async def async_step_import(
        self, import_info: Mapping[str, Any]
    ) -> ConfigFlowResult:
        """Import config from configuration.yaml."""
        _LOGGER.debug("Starting async_step_import - %s", import_info)
        if import_info[CONF_URL] == "":
            import_info[CONF_URL] = None
        await self.async_set_unique_id(import_info[CONF_NAME])
        ir.async_create_issue(
            hass=self.hass,
            domain=DOMAIN,
            issue_id=f"remove_configuration_yaml_{import_info[CONF_NAME]}",
            is_fixable=True,
            is_persistent=True,
            issue_domain=DOMAIN,
            severity=ir.IssueSeverity.WARNING,
            translation_key="remove_configuration_yaml",
            translation_placeholders={
                "domain": DOMAIN,
                "integration_title": import_info[CONF_NAME],
            },
        )
        self._abort_if_unique_id_configured()
        if exclude := import_info.pop(CONF_CONTAINERS_EXCLUDE, None):
            import_info[CONF_CONTAINERS] = [
                container
                for container in import_info[CONF_CONTAINERS]
                if container not in exclude
            ]
        for key, value in import_info.items():
            if key in self.data and key not in [CONF_CONTAINERS_EXCLUDE]:
                self.data[key] = value
        return self.async_create_entry(title=self.data[CONF_NAME], data=self.data)
