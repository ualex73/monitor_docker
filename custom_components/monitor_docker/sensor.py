"""Docker Monitor sensor component."""

import asyncio
import logging
import re
from datetime import datetime
from typing import Any

from homeassistant.components.sensor import (
    ENTITY_ID_FORMAT,
    SensorEntity,
    SensorEntityDescription,
)
from homeassistant.const import CONF_MONITORED_CONDITIONS, CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType
from homeassistant.util import slugify

from .const import (
    API,
    ATTR_MEMORY_LIMIT,
    ATTR_ONLINE_CPUS,
    ATTR_VERSION_ARCH,
    ATTR_VERSION_KERNEL,
    ATTR_VERSION_OS,
    ATTR_VERSION_OS_TYPE,
    CONF_CONTAINERS,
    CONF_CONTAINERS_EXCLUDE,
    CONF_PREFIX,
    CONF_RENAME,
    CONF_RENAME_ENITITY,
    CONF_SENSORNAME,
    CONFIG,
    CONTAINER,
    CONTAINER_INFO_ALLINONE,
    CONTAINER_INFO_HEALTH,
    CONTAINER_INFO_IMAGE,
    CONTAINER_INFO_NETWORK_AVAILABLE,
    CONTAINER_INFO_STATE,
    CONTAINER_INFO_STATUS,
    CONTAINER_INFO_UPTIME,
    CONTAINER_MONITOR_LIST,
    CONTAINER_MONITOR_NETWORK_LIST,
    DOCKER_INFO_VERSION,
    DOCKER_MONITOR_LIST,
    DOMAIN,
)
from .helpers import DockerAPI, DockerContainerAPI

_LOGGER = logging.getLogger(__name__)


async def async_setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    async_add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
):
    """Set up the Monitor Docker Sensor."""

    def find_rename(d: dict[str, str], item: str) -> str:
        for k in d:
            if re.match(k, item):
                return d[k]

        return item

    if discovery_info is None:
        return

    instance: str = discovery_info[CONF_NAME]
    name: str = discovery_info[CONF_NAME]
    api: DockerAPI = hass.data[DOMAIN][name][API]
    config: ConfigType = hass.data[DOMAIN][name][CONFIG]

    # Set or overrule prefix
    prefix = name
    if config[CONF_PREFIX]:
        prefix = config[CONF_PREFIX]

    _LOGGER.debug("[%s]: Setting up sensor(s)", instance)

    sensors = []
    sensors: list[DockerSensor | DockerContainerSensor] = [
        DockerSensor(api, instance, prefix, DOCKER_MONITOR_LIST[variable])
        for variable in config[CONF_MONITORED_CONDITIONS]
        if variable in DOCKER_MONITOR_LIST
        if CONTAINER not in discovery_info
    ]

    # We support add/re-add of a container
    if CONTAINER in discovery_info:
        clist = [discovery_info[CONTAINER]]
    else:
        clist = api.list_containers()

    allinone = False
    stateremoved = False

    # Detect allinone
    if CONTAINER_INFO_ALLINONE in config[CONF_MONITORED_CONDITIONS]:
        allinone = True
        config[CONF_MONITORED_CONDITIONS].remove(CONTAINER_INFO_ALLINONE)
        if CONTAINER_INFO_STATE in config[CONF_MONITORED_CONDITIONS]:
            stateremoved = True
            config[CONF_MONITORED_CONDITIONS].remove(CONTAINER_INFO_STATE)

    for cname in clist:
        includeContainer = False
        if cname in config[CONF_CONTAINERS] or not config[CONF_CONTAINERS]:
            includeContainer = True

        if config[CONF_CONTAINERS_EXCLUDE] and cname in config[CONF_CONTAINERS_EXCLUDE]:
            includeContainer = False

        if includeContainer:
            # Try to figure out if we should include any network sensors
            capi = api.get_container(cname)
            info = capi.get_info()
            network_available = info.get(CONTAINER_INFO_NETWORK_AVAILABLE)
            if network_available is None:
                _LOGGER.error(
                    "[%s] %s: Cannot determine network-available?", instance, cname
                )
                network_available = False

            _LOGGER.debug("[%s] %s: Adding component Sensor(s)", instance, cname)

            if allinone:
                monitor_conditions = []
                for variable in config[CONF_MONITORED_CONDITIONS]:
                    if variable in CONTAINER_MONITOR_LIST and (
                        network_available
                        or (
                            not network_available
                            and variable not in CONTAINER_MONITOR_NETWORK_LIST
                        )
                    ):
                        monitor_conditions += [variable]

                # Only force rename of entityid is requested, to not break backwards compatibility
                alias_entityid = cname
                if config[CONF_RENAME_ENITITY]:
                    alias_entityid = find_rename(config[CONF_RENAME], cname)

                sensors += [
                    DockerContainerSensor(
                        capi,
                        instance=instance,
                        prefix=prefix,
                        cname=cname,
                        alias_entityid=alias_entityid,
                        alias_name=find_rename(config[CONF_RENAME], cname),
                        description=CONTAINER_MONITOR_LIST[CONTAINER_INFO_ALLINONE],
                        sensor_name_format=config[CONF_SENSORNAME],
                        condition_list=monitor_conditions,
                    )
                ]
            else:
                for variable in config[CONF_MONITORED_CONDITIONS]:
                    if variable in CONTAINER_MONITOR_LIST and (
                        network_available
                        or (
                            not network_available
                            and variable not in CONTAINER_MONITOR_NETWORK_LIST
                        )
                    ):

                        # Only force rename of entityid is requested, to not break backwards compatibility
                        alias_entityid = cname
                        if config[CONF_RENAME_ENITITY]:
                            alias_entityid = find_rename(config[CONF_RENAME], cname)

                        sensors += [
                            DockerContainerSensor(
                                capi,
                                instance=instance,
                                prefix=prefix,
                                cname=cname,
                                alias_entityid=alias_entityid,
                                alias_name=find_rename(config[CONF_RENAME], cname),
                                description=CONTAINER_MONITOR_LIST[variable],
                                sensor_name_format=config[CONF_SENSORNAME],
                            )
                        ]

    # Restore state, required for destroy/create container
    if allinone:
        config[CONF_MONITORED_CONDITIONS].append(CONTAINER_INFO_ALLINONE)
    if stateremoved:
        config[CONF_MONITORED_CONDITIONS].append(CONTAINER_INFO_STATE)

    async_add_entities(sensors, True)

    return True


#################################################################
class DockerSensor(SensorEntity):
    """Representation of a Docker Sensor."""

    def __init__(
        self,
        api: DockerAPI,
        instance: str,
        prefix: str,
        description: SensorEntityDescription,
    ):
        """Initialize the sensor."""

        self._api = api
        self._instance = instance
        self._prefix = prefix

        self.entity_description = description

        self._entity_id: str = ENTITY_ID_FORMAT.format(
            slugify(f"{self._prefix}_{self.entity_description.name}")
        )
        self._name = "{name} {sensor}".format(
            name=self._prefix, sensor=self.entity_description
        )

        self._state = None
        self._attributes: dict[str, Any] = {}
        self._removed = False

        _LOGGER.info(
            "[%s]: Initializing Docker sensor '%s'",
            self._instance,
            self.entity_description.name,
        )

    @property
    def entity_id(self) -> str:
        """Return the entity id of the sensor."""
        return self._entity_id

    @property
    def native_value(self) -> str | None:
        """Return the state of the sensor."""
        return self._state

    def update(self) -> None:
        """Get the latest data for the states."""
        info = self._api.get_info()

        if self.entity_description.key == DOCKER_INFO_VERSION:
            self._state = info.get(self.entity_description.key)
            self._attributes[ATTR_MEMORY_LIMIT] = info.get(ATTR_MEMORY_LIMIT)
            self._attributes[ATTR_ONLINE_CPUS] = info.get(ATTR_ONLINE_CPUS)
            self._attributes[ATTR_VERSION_ARCH] = info.get(ATTR_VERSION_ARCH)
            self._attributes[ATTR_VERSION_OS] = info.get(ATTR_VERSION_OS)
            self._attributes[ATTR_VERSION_OS_TYPE] = info.get(ATTR_VERSION_OS_TYPE)
            self._attributes[ATTR_VERSION_KERNEL] = info.get(ATTR_VERSION_KERNEL)
        else:
            self._state = info.get(self.entity_description.key)

    @property
    def extra_state_attributes(self) -> dict:
        """Return the state attributes."""
        return self._attributes

    async def async_added_to_hass(self) -> None:
        """Register callbacks."""
        self._api.register_callback(self.event_callback, self.entity_description.key)

    def event_callback(self, remove=False) -> None:
        """Callback to remove Docker entity."""

        # If already called before, do not remove it again
        if self._removed:
            return

        if remove:
            _LOGGER.info(
                "[%s]: Removing sensor entity: %s",
                self._instance,
                self.entity_description.key,
            )
            asyncio.create_task(self.async_remove())
            self._removed = True
            return


#################################################################
class DockerContainerSensor(SensorEntity):
    """Representation of a Docker Sensor."""

    def __init__(
        self,
        container: DockerContainerAPI,
        instance: str,
        prefix: str,
        cname: str,
        alias_entityid: str,
        alias_name: str,
        description: SensorEntityDescription,
        sensor_name_format: str,
        condition_list: list | None = None,
    ):
        """Initialize the sensor."""

        self._instance = instance
        self._container = container
        self._prefix = prefix
        self._cname = cname
        self._condition_list = condition_list

        self.entity_description = description

        if self.entity_description.key == CONTAINER_INFO_ALLINONE:
            self._entity_id = ENTITY_ID_FORMAT.format(
                slugify(f"{self._prefix}_{alias_entityid}")
            )
            self._attr_name = ENTITY_ID_FORMAT.format(
                slugify(f"{self._prefix}_{alias_entityid}")
            )
            self._attr_name = sensor_name_format.format(
                name=alias_name, sensorname="", sensor=""
            )
        else:
            self._entity_id = ENTITY_ID_FORMAT.format(
                slugify(
                    f"{self._prefix}_{alias_entityid}_{self.entity_description.name}"
                )
            )
            self._attr_name = sensor_name_format.format(
                name=alias_name,
                sensorname=self.entity_description.name,
                sensor=self.entity_description.name,
            )

        self._state = None
        self._state_extra = None

        self._attr_extra_state_attributes: dict[str, Any] = {}
        self._removed = False

        _LOGGER.info(
            "[%s] %s: Initializing sensor with parameter: %s",
            self._instance,
            self._cname,
            self.entity_description.name,
        )

    @property
    def entity_id(self) -> str:
        """Return the entity id of the sensor."""
        return self._entity_id

    @property
    def icon(self) -> str:
        """Icon to use in the frontend, if any."""
        if self.entity_description.key == CONTAINER_INFO_STATUS:
            if self._state_extra == "running":
                return "mdi:checkbox-marked-circle-outline"
            else:
                return "mdi:checkbox-blank-circle-outline"
        elif self.entity_description.key in [
            CONTAINER_INFO_ALLINONE,
            CONTAINER_INFO_STATE,
        ]:
            if self._state == "running":
                return "mdi:checkbox-marked-circle-outline"
            else:
                return "mdi:checkbox-blank-circle-outline"

        return self.entity_description.icon

    @property
    def should_poll(self) -> bool:
        return False

    @property
    def native_value(self) -> str:
        """Return the state of the sensor."""
        return self._state

    async def async_added_to_hass(self) -> None:
        """Register callbacks."""
        self._container.register_callback(
            self.event_callback, self.entity_description.key
        )

        # Call event callback for possible information available
        self.event_callback()

    def event_callback(self, name="", remove=False) -> None:
        """Callback for update of container information."""

        if remove:
            # If already called before, do not remove it again
            if self._removed:
                return

            _LOGGER.info(
                "[%s] %s: Removing sensor entity: %s",
                self._instance,
                self._cname,
                self.entity_description.key,
            )
            asyncio.create_task(self.async_remove())
            self._removed = True
            return

        state = None

        _LOGGER.debug(
            "[%s] %s: Received callback for: %s",
            self._instance,
            self._cname,
            self.entity_description.key,
        )

        stats = {}

        try:
            info = self._container.get_info()

            if info.get(CONTAINER_INFO_STATE) == "running":
                stats = self._container.get_stats()

        except Exception as err:
            _LOGGER.error(
                "[%s] %s: Cannot request container info (%s)",
                self._instance,
                self._cname,
                str(err),
            )
        else:
            if self.entity_description.key == CONTAINER_INFO_ALLINONE:
                # The state is mandatory
                state = info.get(CONTAINER_INFO_STATE)

                # Now list the rest of the attributes
                self._attr_extra_state_attributes = {}
                for cond in self._condition_list:
                    if cond in [
                        CONTAINER_INFO_STATUS,
                        CONTAINER_INFO_IMAGE,
                        CONTAINER_INFO_HEALTH,
                        CONTAINER_INFO_UPTIME,
                    ]:
                        self._attr_extra_state_attributes[cond] = info.get(cond, None)
                    else:
                        self._attr_extra_state_attributes[cond] = stats.get(cond, None)
            elif self.entity_description.key == CONTAINER_INFO_STATUS:
                state = info.get(CONTAINER_INFO_STATUS)
                self._state_extra = info.get(CONTAINER_INFO_STATE)
            elif self.entity_description.key in [
                CONTAINER_INFO_STATE,
                CONTAINER_INFO_IMAGE,
                CONTAINER_INFO_HEALTH,
            ]:
                state = info.get(self.entity_description.key)
            elif info.get(CONTAINER_INFO_STATE) == "running":
                if self.entity_description.key in CONTAINER_MONITOR_LIST:
                    if self.entity_description.key in [CONTAINER_INFO_UPTIME]:
                        state = datetime.fromisoformat(
                            info.get(self.entity_description.key)
                        )
                    else:
                        state = stats.get(self.entity_description.key)

        if (
            state != self._state
            or self.entity_description.key == CONTAINER_INFO_ALLINONE
        ):
            self._state = state

            try:
                self.schedule_update_ha_state()
            except Exception as err:
                _LOGGER.error(
                    "[%s] %s: Failed 'schedule_update_ha_state' (%s)",
                    self._instance,
                    self._cname,
                    str(err),
                )
