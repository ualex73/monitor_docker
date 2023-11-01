"""Monitor Docker main component."""
import asyncio
import logging
import threading
import time
from datetime import timedelta

import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from homeassistant.const import CONF_MONITORED_CONDITIONS
from homeassistant.const import CONF_NAME
from homeassistant.const import CONF_SCAN_INTERVAL
from homeassistant.const import CONF_URL

from .const import API
from .const import CONF_CERTPATH
from .const import CONF_CONTAINERS
from .const import CONF_CONTAINERS_EXCLUDE
from .const import CONF_MEMORYCHANGE
from .const import CONF_PRECISION_CPU
from .const import CONF_PRECISION_MEMORY_MB
from .const import CONF_PRECISION_MEMORY_PERCENTAGE
from .const import CONF_PRECISION_NETWORK_KB
from .const import CONF_PRECISION_NETWORK_MB
from .const import CONF_PREFIX
from .const import CONF_RENAME
from .const import CONF_RETRY
from .const import CONF_SENSORNAME
from .const import CONF_SWITCHENABLED
from .const import CONF_SWITCHNAME
from .const import CONFIG
from .const import CONTAINER_INFO_ALLINONE
from .const import DEFAULT_NAME
from .const import DEFAULT_RETRY
from .const import DEFAULT_SENSORNAME
from .const import DEFAULT_SWITCHNAME
from .const import DOMAIN
from .const import MONITORED_CONDITIONS_LIST
from .const import PRECISION
from .helpers import DockerAPI

_LOGGER = logging.getLogger(__name__)

DEFAULT_SCAN_INTERVAL = timedelta(seconds=10)

DOCKER_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
        vol.Optional(CONF_PREFIX, default=''): cv.string,
        vol.Optional(CONF_URL, default=None): vol.Any(cv.string, None),
        vol.Optional(CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL): cv.time_period,  # noqa: E501
        vol.Optional(
            CONF_MONITORED_CONDITIONS, default=MONITORED_CONDITIONS_LIST,
        ): vol.All(
            cv.ensure_list,
            [vol.In(MONITORED_CONDITIONS_LIST + list([CONTAINER_INFO_ALLINONE]))],  # noqa: E501
        ),
        vol.Optional(CONF_CONTAINERS, default=[]): cv.ensure_list,
        vol.Optional(CONF_CONTAINERS_EXCLUDE, default=[]): cv.ensure_list,
        vol.Optional(CONF_RENAME, default={}): dict,
        vol.Optional(CONF_SENSORNAME, default=DEFAULT_SENSORNAME): cv.string,
        vol.Optional(CONF_SWITCHENABLED, default=True): vol.Any(
            cv.boolean, cv.ensure_list(cv.string),
        ),
        vol.Optional(CONF_SWITCHNAME, default=DEFAULT_SWITCHNAME): cv.string,
        vol.Optional(CONF_CERTPATH, default=''): cv.string,
        vol.Optional(CONF_RETRY, default=DEFAULT_RETRY): cv.positive_int,
        vol.Optional(CONF_MEMORYCHANGE, default=100): cv.positive_int,
        vol.Optional(CONF_PRECISION_CPU, default=PRECISION): cv.positive_int,
        vol.Optional(CONF_PRECISION_MEMORY_MB, default=PRECISION): cv.positive_int,  # noqa: E501
        vol.Optional(
            CONF_PRECISION_MEMORY_PERCENTAGE, default=PRECISION,
        ): cv.positive_int,
        vol.Optional(CONF_PRECISION_NETWORK_KB, default=PRECISION): cv.positive_int,  # noqa: E501
        vol.Optional(CONF_PRECISION_NETWORK_MB, default=PRECISION): cv.positive_int,  # noqa: E501
    },
)

CONFIG_SCHEMA = vol.Schema(
    {DOMAIN: vol.All(cv.ensure_list, [vol.Any(DOCKER_SCHEMA)])},
    extra=vol.ALLOW_EXTRA,
)


#################################################################
async def async_setup(hass, config):
    """Will setup the Monitor Docker platform."""

    def RunDocker(hass, entry):
        """Wrapper around function for a separated thread."""

        # Create out asyncio loop, because we are already inside
        # a def (not main) we need to do create/set
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        # Create docker instance, it will have asyncio threads
        hass.data[DOMAIN][entry[CONF_NAME]] = {}
        hass.data[DOMAIN][entry[CONF_NAME]][CONFIG] = entry

        startCount = 0

        while True:
            doLoop = True

            try:
                hass.data[DOMAIN][entry[CONF_NAME]][API] = DockerAPI(
                    hass, entry, startCount,
                )
            except Exception as err:
                doLoop = False
                if entry[CONF_RETRY] == 0:
                    raise
                else:
                    _LOGGER.error('Failed Docker connect: %s', str(err))
                    _LOGGER.error('Retry in %d seconds', entry[CONF_RETRY])
                    time.sleep(entry[CONF_RETRY])

            startCount += 1

            if doLoop:
                # Now run forever in this separated thread
                loop.run_forever()

                # We only get here if a docker instance disconnected or HASS is stopping  # noqa: E501
                if not hass.data[DOMAIN][entry[CONF_NAME]][API]._dockerStopped:
                    # If HASS stopped, do not retry
                    break

    # Create domain monitor_docker data variable
    hass.data[DOMAIN] = {}

    # Now go through all possible entries, we support 1 or more docker hosts (untested)  # noqa: E501
    for entry in config[DOMAIN]:
        # Check if CONF_MONITORED_CONDITIONS has only ALLINONE, then expand to all  # noqa: E501
        if (
            len(entry[CONF_MONITORED_CONDITIONS]) == 1
            and CONTAINER_INFO_ALLINONE in entry[CONF_MONITORED_CONDITIONS]
        ):
            entry[CONF_MONITORED_CONDITIONS] = list(MONITORED_CONDITIONS_LIST) + list(  # noqa: E501
                [CONTAINER_INFO_ALLINONE],
            )

        if entry[CONF_NAME] in hass.data[DOMAIN]:
            _LOGGER.error(
                'Instance %s is duplicate, please assign an unique name',
                entry[CONF_NAME],
            )
            return False

        # Each docker hosts runs in its own thread. We need to pass hass too, for the load_platform  # noqa: E501
        thread = threading.Thread(
            target=RunDocker, kwargs={'hass': hass, 'entry': entry},
        )
        thread.start()

    return True
