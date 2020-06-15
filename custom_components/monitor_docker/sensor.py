"""Docker Monitor sensor component."""

import asyncio
import logging

from homeassistant.components.sensor import ENTITY_ID_FORMAT
from homeassistant.const import CONF_NAME, CONF_MONITORED_CONDITIONS
from homeassistant.helpers.entity import Entity
from homeassistant.util import slugify

from .const import (
    DOMAIN,
    API,
    ATTR_MEMORY_LIMIT,
    ATTR_ONLINE_CPUS,
    ATTR_VERSION_ARCH,
    ATTR_VERSION_KERNEL,
    ATTR_VERSION_OS,
    ATTR_VERSION_OS_TYPE,
    CONFIG,
    CONF_CONTAINERS,
    CONF_RENAME,
    CONF_SENSORNAME,
    DOCKER_INFO_VERSION,
    CONTAINER,
    CONTAINER_INFO_IMAGE,
    CONTAINER_INFO_NETWORKMODE,
    CONTAINER_INFO_STATE,
    CONTAINER_INFO_STATUS,
    CONTAINER_INFO_UPTIME,
    CONTAINER_MONITOR_LIST,
    CONTAINER_MONITOR_NETWORK_LIST,
    DOCKER_MONITOR_LIST,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Set up the Monitor Docker Sensor."""

    if discovery_info is None:
        return

    name = discovery_info[CONF_NAME]
    api = hass.data[DOMAIN][name][API]
    config = hass.data[DOMAIN][name][CONFIG]
    prefix = config[CONF_NAME]

    sensors = []
    sensors = [
        DockerSensor(api, prefix, variable)
        for variable in config[CONF_MONITORED_CONDITIONS]
        if variable in DOCKER_MONITOR_LIST
        if CONTAINER not in discovery_info
    ]

    # We support add/re-add of a container
    if CONTAINER in discovery_info:
        clist = [discovery_info[CONTAINER]]
    else:
        clist = api.list_containers()

    for cname in clist:
        if cname in config[CONF_CONTAINERS]:
            # Try to figure out if we should include any network sensors
            capi = api.get_container(cname)
            info = capi.get_info()
            networkmode = info.get(CONTAINER_INFO_NETWORKMODE)
            if networkmode is None:
                _LOGGER.error("%s: Can not determine networkmode?", cname)
                networkmode = False

            _LOGGER.debug("%s: Adding component Sensor(s)", cname)
            for variable in config[CONF_MONITORED_CONDITIONS]:
                if variable in CONTAINER_MONITOR_LIST and (
                    not networkmode
                    or (networkmode and variable not in CONTAINER_MONITOR_NETWORK_LIST)
                ):
                    sensors += [
                        DockerContainerSensor(
                            capi,
                            prefix,
                            cname,
                            config[CONF_RENAME].get(cname, cname),
                            variable,
                            config[CONF_SENSORNAME],
                        )
                    ]

    async_add_entities(sensors, True)

    return True


class DockerSensor(Entity):
    """Representation of a Docker Sensor."""

    def __init__(self, api, prefix, variable):
        """Initialize the sensor."""
        self._api = api
        self._prefix = prefix

        self._var_id = variable
        self._var_name = DOCKER_MONITOR_LIST[variable][0]
        self._var_unit = DOCKER_MONITOR_LIST[variable][1]
        self._var_icon = DOCKER_MONITOR_LIST[variable][2]
        self._var_class = DOCKER_MONITOR_LIST[variable][3]
        self._entity_id = ENTITY_ID_FORMAT.format(
            slugify(self._prefix + "_" + self._var_name)
        )

        self._name = "{name} {sensor}".format(name=self._prefix, sensor=self._var_name)

        self._state = None
        self._attributes = {}

        _LOGGER.info("Initializing Docker sensor '%s'", self._var_id)

    @property
    def entity_id(self):
        """Return the entity id of the sensor."""
        return self._entity_id

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def icon(self):
        """Icon to use in the frontend."""
        return self._var_icon

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state

    @property
    def device_class(self):
        """Return the class of this sensor."""
        return self._var_class

    @property
    def unit_of_measurement(self):
        """Return the unit the value is expressed in."""
        return self._var_unit

    def update(self):
        """Get the latest data for the states."""
        info = self._api.get_info()

        if self._var_id == DOCKER_INFO_VERSION:
            self._state = info.get(self._var_id)
            self._attributes[ATTR_MEMORY_LIMIT] = info.get(ATTR_MEMORY_LIMIT)
            self._attributes[ATTR_ONLINE_CPUS] = info.get(ATTR_ONLINE_CPUS)
            self._attributes[ATTR_VERSION_ARCH] = info.get(ATTR_VERSION_ARCH)
            self._attributes[ATTR_VERSION_OS] = info.get(ATTR_VERSION_OS)
            self._attributes[ATTR_VERSION_OS_TYPE] = info.get(ATTR_VERSION_OS_TYPE)
            self._attributes[ATTR_VERSION_KERNEL] = info.get(ATTR_VERSION_KERNEL)
        else:
            self._state = info.get(self._var_id)

    @property
    def device_state_attributes(self):
        """Return the state attributes."""
        return self._attributes


class DockerContainerSensor(Entity):
    """Representation of a Docker Sensor."""

    def __init__(self, container, prefix, cname, alias, variable, sensor_name_format):
        """Initialize the sensor."""
        self._loop = asyncio.get_running_loop()
        self._container = container
        self._prefix = prefix
        self._cname = cname

        self._var_id = variable
        self._var_name = CONTAINER_MONITOR_LIST[variable][0]
        self._var_unit = CONTAINER_MONITOR_LIST[variable][1]
        self._var_icon = CONTAINER_MONITOR_LIST[variable][2]
        self._var_class = CONTAINER_MONITOR_LIST[variable][3]
        self._state_extra = None

        self._entity_id = ENTITY_ID_FORMAT.format(
            slugify(self._prefix + "_" + self._cname + "_" + self._var_name)
        )
        self._name = sensor_name_format.format(
            name=alias, sensorname=self._var_name, sensor=self._var_name
        )

        self._state = None
        self._state_extra = None

        self._attributes = {}

        _LOGGER.info(
            "%s: Initializing sensor with parameter: %s", self._cname, self._var_name
        )

    @property
    def entity_id(self):
        """Return the entity id of the cover."""
        return self._entity_id

    @property
    def name(self):
        """Return the name of the sensor, if any."""
        return self._name

    @property
    def icon(self):
        """Icon to use in the frontend, if any."""
        if self._var_id == CONTAINER_INFO_STATUS:
            if self._state_extra == "running":
                return "mdi:checkbox-marked-circle-outline"
            else:
                return "mdi:checkbox-blank-circle-outline"

        return self._var_icon

    @property
    def should_poll(self):
        return False

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state

    @property
    def device_class(self):
        """Return the class of this sensor."""
        return self._var_class

    @property
    def unit_of_measurement(self):
        """Return the unit the value is expressed in."""
        return self._var_unit

    @property
    def device_state_attributes(self):
        """Return the state attributes."""
        return self._attributes

    async def async_added_to_hass(self):
        """Register callbacks."""
        self._container.register_callback(self.event_callback, self._var_id)

        # Call event callback for possible information available
        self.event_callback()

    def event_callback(self, remove=False):
        """Callback for update of container information."""

        if remove:
            _LOGGER.error("%s: Removing sensor entity: %s", self._cname, self._var_id)
            self._loop.create_task(self.async_remove())
            return

        state = None

        _LOGGER.debug("%s: Received callback for: %s", self._cname, self._var_name)

        stats = {}

        try:
            info = self._container.get_info()

            if info.get(CONTAINER_INFO_STATE) == "running":
                stats = self._container.get_stats()

        except Exception as err:
            _LOGGER.error("%s: Cannot request container info", str(err))
        else:
            if self._var_id == CONTAINER_INFO_STATUS:
                state = info.get(CONTAINER_INFO_STATUS)
                self._state_extra = info.get(CONTAINER_INFO_STATE)
            elif info.get(CONTAINER_INFO_STATE) == "running":
                if self._var_id in CONTAINER_MONITOR_LIST:
                    if self._var_id in [CONTAINER_INFO_STATE, CONTAINER_INFO_UPTIME, CONTAINER_INFO_IMAGE]:
                        state = info.get(self._var_id)
                    else:
                        state = stats.get(self._var_id)

        if state != self._state:
            self._state = state

            try:
                self.schedule_update_ha_state()
            except Exception as err:
                _LOGGER.error(
                    "Failed 'schedule_update_ha_state' %s", str(err), exc_info=True
                )
