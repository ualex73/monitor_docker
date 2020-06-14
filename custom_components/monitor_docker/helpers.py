"""Monitor Docker API helper."""

import aiodocker
import asyncio
import concurrent
import logging

from datetime import datetime, timezone
from dateutil import parser, relativedelta

from homeassistant.helpers.discovery import load_platform

import homeassistant.util.dt as dt_util

from homeassistant.const import (
    CONF_NAME,
    CONF_SCAN_INTERVAL,
    CONF_URL,
    EVENT_HOMEASSISTANT_STOP,
)

from .const import (
    ATTR_MEMORY_LIMIT,
    ATTR_ONLINE_CPUS,
    ATTR_VERSION_ARCH,
    ATTR_VERSION_KERNEL,
    ATTR_VERSION_OS,
    ATTR_VERSION_OS_TYPE,
    COMPONENTS,
    CONTAINER,
    CONTAINER_STATS_CPU_PERCENTAGE,
    CONTAINER_INFO_IMAGE,
    CONTAINER_INFO_NETWORKMODE,
    CONTAINER_STATS_MEMORY,
    CONTAINER_STATS_MEMORY_PERCENTAGE,
    CONTAINER_STATS_NETWORK_SPEED_UP,
    CONTAINER_STATS_NETWORK_SPEED_DOWN,
    CONTAINER_STATS_NETWORK_TOTAL_UP,
    CONTAINER_STATS_NETWORK_TOTAL_DOWN,
    CONTAINER_INFO_STATE,
    CONTAINER_INFO_STATUS,
    CONTAINER_INFO_UPTIME,
    DOCKER_INFO_CONTAINER_RUNNING,
    DOCKER_INFO_CONTAINER_TOTAL,
    DOCKER_INFO_VERSION,
    DOCKER_STATS_CPU_PERCENTAGE,
    DOCKER_STATS_MEMORY,
    DOCKER_STATS_MEMORY_PERCENTAGE,
    DOMAIN,
    PRECISION,
)

_LOGGER = logging.getLogger(__name__)


def toKB(value):
    """Converts bytes to kBytes."""
    return round(value / (1024 ** 1), PRECISION)


def toMB(value):
    """Converts bytes to MBytes."""
    return round(value / (1024 ** 2), PRECISION)


#################################################################
class DockerAPI:
    """Docker API abstraction allowing multiple Docker instances beeing monitored."""

    def __init__(self, hass, config):
        """Initialize the Docker API."""

        self._hass = hass
        self._config = config
        self._containers = {}
        self._tasks = {}
        self._info = {}

        self._interval = config[CONF_SCAN_INTERVAL].seconds

        self._loop = asyncio.get_event_loop()

        try:
            self._api = aiodocker.Docker(url=self._config[CONF_URL])
        except Exception as err:
            _LOGGER.error("Can not connect to Docker API (%s)", str(err))
            return

        version = self._loop.run_until_complete(self._api.version())
        _LOGGER.debug("Docker version: %s", version.get("Version", None))

        # Start task to monitor events of create/delete/start/stop
        self._tasks["events"] = self._loop.create_task(self._run_docker_events())

        # Start task to monitor total/running containers
        self._tasks["info"] = self._loop.create_task(self._run_docker_info())

        # Get the list of containers to monitor
        containers = self._loop.run_until_complete(self._api.containers.list(all=True))

        for container in containers or []:
            # Determine name from Docker API, it contains an array with a slash
            cname = container._container["Names"][0][1:]

            # We will monitor all containers, including excluded ones.
            # This is needed to get total CPU/Memory usage.
            _LOGGER.debug("%s: Container Monitored", cname)

            # Create our Docker Container API
            self._containers[cname] = DockerContainerAPI(
                self._api, cname, self._interval
            )

        hass.bus.listen_once(EVENT_HOMEASSISTANT_STOP, self._monitor_stop)

        for component in COMPONENTS:
            load_platform(
                self._hass,
                component,
                DOMAIN,
                {CONF_NAME: self._config[CONF_NAME]},
                self._config,
            )

    #############################################################
    def _monitor_stop(self, _service_or_event):
        """Stop the monitor thread."""
        _LOGGER.info("Stopping Monitor Docker thread (%s)", self._config[CONF_NAME])

        self._loop.stop()

    #############################################################
    async def _run_docker_events(self):
        """Function to retrieve docker events. We can add or remove monitored containers."""

        try:
            while True:
                subscriber = self._api.events.subscribe()

                event = await subscriber.get()
                if event is None:
                    break

                # Only monitor container events
                if event["Type"] == "container":
                    if event["Action"] == "create":
                        cname = event["Actor"]["Attributes"]["name"]
                        await self._container_add(cname)

                        for component in COMPONENTS:
                            load_platform(
                                self._hass,
                                component,
                                DOMAIN,
                                {CONF_NAME: self._config[CONF_NAME], CONTAINER: cname},
                                self._config,
                            )

                    if event["Action"] == "destroy":
                        cname = event["Actor"]["Attributes"]["name"]
                        await self._container_remove(cname)
        except Exception as err:
            _LOGGER.error(" run_docker_events (%s)", str(err), exc_info=True)

    #############################################################
    async def _container_add(self, cname):

        if cname in self._containers:
            _LOGGER.error("%s: Container already monitored", cname)
            return

        _LOGGER.debug("%s: Starting Container Monitor", cname)

        # Create our Docker Container API
        self._containers[cname] = DockerContainerAPI(
            self._api, cname, self._interval, False
        )

    #############################################################
    async def _container_remove(self, cname):

        if cname in self._containers:
            _LOGGER.debug("%s: Stopping Container Monitor", cname)
            self._containers[cname].cancel_task()
            self._containers[cname].remove_entities()
            await asyncio.sleep(0.1)
            del self._containers[cname]
        else:
            _LOGGER.error("%s: Container is NOT monitored", cname)

    #############################################################
    async def _run_docker_info(self):
        """Function to retrieve information like docker info."""

        try:
            while True:
                info = await self._api.system.info()
                self._info[DOCKER_INFO_VERSION] = info.get("ServerVersion")
                self._info[DOCKER_INFO_CONTAINER_RUNNING] = info.get(
                    "ContainersRunning"
                )
                self._info[DOCKER_INFO_CONTAINER_TOTAL] = info.get("Containers")

                self._info[ATTR_MEMORY_LIMIT] = info.get("MemTotal")
                self._info[ATTR_ONLINE_CPUS] = info.get("NCPU")
                self._info[ATTR_VERSION_OS] = info.get("OperationSystem")
                self._info[ATTR_VERSION_OS_TYPE] = info.get("OStype")
                self._info[ATTR_VERSION_ARCH] = info.get("Architecture")
                self._info[ATTR_VERSION_KERNEL] = info.get("KernelVersion")

                self._info[DOCKER_STATS_CPU_PERCENTAGE] = 0.0
                self._info[DOCKER_STATS_MEMORY] = 0
                self._info[DOCKER_STATS_MEMORY_PERCENTAGE] = 0.0

                # Now go through all containers and get the cpu/memory stats
                for container in self._containers.values():
                    try:
                        info = container.get_info()
                        if info.get(CONTAINER_INFO_STATE) == "running":
                            stats = container.get_stats()
                            if stats.get(CONTAINER_STATS_CPU_PERCENTAGE) is not None:
                                self._info[DOCKER_STATS_CPU_PERCENTAGE] += stats.get(
                                    CONTAINER_STATS_CPU_PERCENTAGE
                                )
                            if stats.get(CONTAINER_STATS_MEMORY) is not None:
                                self._info[DOCKER_STATS_MEMORY] += stats.get(
                                    CONTAINER_STATS_MEMORY
                                )
                            if stats.get(CONTAINER_STATS_MEMORY_PERCENTAGE) is not None:
                                self._info[DOCKER_STATS_MEMORY_PERCENTAGE] += stats.get(
                                    CONTAINER_STATS_MEMORY_PERCENTAGE
                                )
                    except Exception as err:
                        _LOGGER.error(
                            "%s: run_docker_info memory/cpu of X (%s)",
                            self._config[CONF_NAME],
                            str(err),
                            exc_info=True,
                        )

                # Try to fix possible 0 values in history at start-up
                self._info[DOCKER_STATS_CPU_PERCENTAGE] = (
                    None
                    if self._info[DOCKER_STATS_CPU_PERCENTAGE] == 0.0
                    else round(self._info[DOCKER_STATS_CPU_PERCENTAGE], PRECISION)
                )
                self._info[DOCKER_STATS_MEMORY] = (
                    None
                    if self._info[DOCKER_STATS_MEMORY] == 0.0
                    else round(self._info[DOCKER_STATS_MEMORY], PRECISION)
                )
                self._info[DOCKER_STATS_MEMORY_PERCENTAGE] = (
                    None
                    if self._info[DOCKER_STATS_MEMORY_PERCENTAGE] == 0.0
                    else round(self._info[DOCKER_STATS_MEMORY_PERCENTAGE], PRECISION)
                )

                _LOGGER.debug(
                    "Version: %s, Containers: %s, Running: %s, CPU: %s%%, Memory: %sMB, %s%%",
                    self._info[DOCKER_INFO_VERSION],
                    self._info[DOCKER_INFO_CONTAINER_TOTAL],
                    self._info[DOCKER_INFO_CONTAINER_RUNNING],
                    self._info[DOCKER_STATS_CPU_PERCENTAGE],
                    self._info[DOCKER_STATS_MEMORY],
                    self._info[DOCKER_STATS_MEMORY_PERCENTAGE],
                )

                await asyncio.sleep(self._interval)
        except Exception as err:
            _LOGGER.error(
                "%s: run_docker_info (%s)",
                self._config[CONF_NAME],
                str(err),
                exc_info=True,
            )

    #############################################################
    def list_containers(self):
        return self._containers.keys()

    #############################################################
    def get_container(self, cname):
        if cname in self._containers:
            return self._containers[cname]
        else:
            _LOGGER.error("Trying to get a not existing container %s", cname)
            return None

    #############################################################
    def get_info(self):
        return self._info


#################################################################
class DockerContainerAPI:
    """Docker Container API abstraction."""

    def __init__(self, api, name, interval, atInit=True):
        self._api = api
        self._name = name
        self._interval = interval
        self._busy = False
        self._atInit = atInit
        self._task = None
        self._subscribers = []
        self._cpu_old = {}
        self._network_old = {}

        self._info = {}
        self._stats = {}

        self._loop = asyncio.get_event_loop()

        # During start-up we will wait on container attachment,
        # preventing concurrency issues the main HA loop (we are
        # othside that one with our threads)
        if self._atInit:
            try:
                self._container = self._loop.run_until_complete(
                    self._api.containers.get(self._name)
                )
            except Exception as err:
                _LOGGER.error(
                    "%s: Container not available anymore (%s)",
                    self._name,
                    str(err),
                    exc_info=True,
                )
                return

        self._task = self._loop.create_task(self._run())

    #############################################################
    async def _run(self):

        # If we noticed a event=create, we need to attach here.
        # The run_until_complete doesn't work, because we are already
        # in a running loop.
        if not self._atInit:
            try:
                self._container = await self._api.containers.get(self._name)
            except Exception as err:
                _LOGGER.error(
                    "%s: Container not available anymore (%s)",
                    self._name,
                    str(err),
                    exc_info=True,
                )
                return

        try:
            while True:

                # Don't check container if we are doing a start/stop
                if not self._busy:
                    await self._run_container_info()

                    # Only run stats if container is running
                    if self._info[CONTAINER_INFO_STATE] in ("running", "paused"):
                        await self._run_container_stats()

                    self._notify()
                else:
                    _LOGGER.debug("%s: Waiting on stop/start of container", self._name)

                await asyncio.sleep(self._interval)
        except concurrent.futures._base.CancelledError:
            pass
        except Exception as err:
            _LOGGER.error(
                "%s: Container not available anymore (%s)",
                self._name,
                str(err),
                exc_info=True,
            )

    #############################################################
    async def _run_container_info(self):
        """Get container information, but we can not get
           the uptime of this container, that is only available
           while listing all containers :-(.
        """

        self._info = {}

        raw = await self._container.show()

        self._info[CONTAINER_INFO_STATE] = raw["State"]["Status"]
        self._info[CONTAINER_INFO_IMAGE] = raw["Config"]["Image"]
        self._info[CONTAINER_INFO_NETWORKMODE] = (
            True if raw["HostConfig"]["NetworkMode"] == "host" else False
        )

        # We only do a calculation of startedAt, because we use it twice
        startedAt = parser.parse(raw["State"]["StartedAt"])

        # Determine the container status in the format:
        # Up 6 days
        # Up 6 days (Paused)
        # Exited (0) 2 months ago
        # Restarting (99) 5 seconds ago

        if self._info[CONTAINER_INFO_STATE] == "running":
            self._info[CONTAINER_INFO_STATUS] = "Up {}".format(
                self._calcdockerformat(startedAt)
            )
        elif self._info[CONTAINER_INFO_STATE] == "exited":
            self._info[CONTAINER_INFO_STATUS] = "Exited ({}) {} ago".format(
                raw["State"]["ExitCode"],
                self._calcdockerformat(parser.parse(raw["State"]["FinishedAt"])),
            )
        elif self._info[CONTAINER_INFO_STATE] == "created":
            self._info[CONTAINER_INFO_STATUS] = "Created {} ago".format(
                self._calcdockerformat(parser.parse(raw["Created"]))
            )
        elif self._info[CONTAINER_INFO_STATE] == "restarting":
            self._info[CONTAINER_INFO_STATUS] = "Restarting"
        elif self._info[CONTAINER_INFO_STATE] == "paused":
            self._info[CONTAINER_INFO_STATUS] = "Up {} (Paused)".format(
                self._calcdockerformat(startedAt)
            )
        else:
            self._info[CONTAINER_INFO_STATUS] = "None ({})".format(
                raw["State"]["Status"]
            )

        if self._info[CONTAINER_INFO_STATE] in ("running", "paused"):
            self._info[CONTAINER_INFO_UPTIME] = dt_util.as_local(startedAt).isoformat()
        else:
            self._info[CONTAINER_INFO_UPTIME] = None
            _LOGGER.debug("%s: %s", self._name, self._info[CONTAINER_INFO_STATUS])

    #############################################################
    async def _run_container_stats(self):

        # Initialize stats information
        stats = {}
        stats["cpu"] = {}
        stats["memory"] = {}
        stats["network"] = {}
        stats["read"] = {}

        # Get container stats, only interested in [0]
        raw = await self._container.stats(stream=False)
        raw = raw[0]

        stats["read"] = parser.parse(raw["read"])

        # Gather CPU information
        cpu_stats = {}
        try:
            cpu_new = {}
            cpu_new["total"] = raw["cpu_stats"]["cpu_usage"]["total_usage"]
            cpu_new["system"] = raw["cpu_stats"]["system_cpu_usage"]

            # Compatibility wih older Docker API
            if "online_cpus" in raw["cpu_stats"]:
                cpu_stats["online_cpus"] = raw["cpu_stats"]["online_cpus"]
            else:
                cpu_stats["online_cpus"] = len(
                    raw["cpu_stats"]["cpu_usage"]["percpu_usage"] or []
                )

            # Calculate cpu usage, but first iteration we don't know it
            if self._cpu_old:
                cpu_delta = float(cpu_new["total"] - self._cpu_old["total"])
                system_delta = float(cpu_new["system"] - self._cpu_old["system"])

                cpu_stats["total"] = round(0.0, PRECISION)
                if cpu_delta > 0.0 and system_delta > 0.0:
                    cpu_stats["total"] = round(
                        (cpu_delta / system_delta)
                        * float(cpu_stats["online_cpus"])
                        * 100.0,
                        PRECISION,
                    )

            self._cpu_old = cpu_new

        except KeyError as err:
            # Something wrong with the raw data
            _LOGGER.error(
                "%s: Can not determine CPU usage for container (%s)",
                self._name,
                str(err),
            )
            if "cpu_stats" in raw:
                _LOGGER.error("Raw 'cpu_stats' %s", raw["cpu_stats"])
            else:
                _LOGGER.error("No 'cpu_stats' found in raw packet")

        # Gather memory information
        memory_stats = {}
        try:
            # Memory is in Bytes, convert to MBytes
            memory_stats["usage"] = toMB(
                raw["memory_stats"]["usage"] - raw["memory_stats"]["stats"]["cache"]
            )
            memory_stats["limit"] = toMB(raw["memory_stats"]["limit"])
            memory_stats["max_usage"] = toMB(raw["memory_stats"]["max_usage"])
            memory_stats["usage_percent"] = round(
                float(memory_stats["usage"]) / float(memory_stats["limit"]) * 100.0,
                PRECISION,
            )

        except (KeyError, TypeError) as err:
            _LOGGER.error(
                "%s: Can not determine memory usage for container (%s)",
                self._name,
                str(err),
            )
            if "memory_stats" in raw:
                _LOGGER.error(
                    "%s: Raw 'memory_stats' %s", raw["memory_stats"], self._name
                )
            else:
                _LOGGER.error("%s: No 'memory_stats' found in raw packet", self._name)

        _LOGGER.debug(
            "%s: CPU Usage=%s%%. Memory Usage=%sMB, %s%%",
            self._name,
            cpu_stats.get("total", None),
            memory_stats.get("usage", None),
            memory_stats.get("usage_percent", None),
        )

        # Gather network information, doesn't work in network=host mode
        network_stats = {}
        if not self._info[CONTAINER_INFO_NETWORKMODE]:
            try:
                network_new = {}
                network_stats["total_tx"] = 0
                network_stats["total_rx"] = 0
                for if_name, data in raw["networks"].items():
                    network_stats["total_tx"] += data["tx_bytes"]
                    network_stats["total_rx"] += data["rx_bytes"]

                network_new = {
                    "read": stats["read"],
                    "total_tx": network_stats["total_tx"],
                    "total_rx": network_stats["total_rx"],
                }

                if self._network_old:
                    tx = network_new["total_tx"] - self._network_old["total_tx"]
                    rx = network_new["total_rx"] - self._network_old["total_rx"]
                    tim = (
                        network_new["read"] - self._network_old["read"]
                    ).total_seconds()

                    # Calculate speed, also convert to kByte/sec
                    network_stats["speed_tx"] = toKB(round(float(tx) / tim, PRECISION))
                    network_stats["speed_rx"] = toKB(round(float(rx) / tim, PRECISION))

                self._network_old = network_new

                # Convert total to MB
                network_stats["total_tx"] = toMB(network_stats["total_tx"])
                network_stats["total_rx"] = toMB(network_stats["total_rx"])

            except KeyError as err:
                _LOGGER.error(
                    "%s: Can not determine network usage for container (%s)",
                    self._name,
                    str(err),
                )
                if "networks" in raw:
                    _LOGGER.error("%s: Raw 'networks' %s", raw["networks"], self._name)
                else:
                    _LOGGER.error("%s: No 'networks' found in raw packet", self._name)

        # All information collected
        stats["cpu"] = cpu_stats
        stats["memory"] = memory_stats
        stats["network"] = network_stats

        stats[CONTAINER_STATS_CPU_PERCENTAGE] = cpu_stats.get("total")
        stats[CONTAINER_STATS_MEMORY] = memory_stats.get("usage")
        stats[CONTAINER_STATS_MEMORY_PERCENTAGE] = memory_stats.get("usage_percent")
        stats[CONTAINER_STATS_NETWORK_SPEED_UP] = network_stats.get("speed_tx")
        stats[CONTAINER_STATS_NETWORK_SPEED_DOWN] = network_stats.get("speed_rx")
        stats[CONTAINER_STATS_NETWORK_TOTAL_UP] = network_stats.get("total_tx")
        stats[CONTAINER_STATS_NETWORK_TOTAL_DOWN] = network_stats.get("total_rx")

        self._stats = stats

    #############################################################
    def cancel_task(self):
        if self._task is not None:
            _LOGGER.info("%s: Cancelling task for container info/stats", self._name)
            self._task.cancel()
        else:
            _LOGGER.info(
                "%s: Task (not running) can not be cancelled for container info/stats",
                self._name,
            )

    #############################################################
    def remove_entities(self):
        if len(self._subscribers) > 0:
            _LOGGER.debug("%s: Removing entities from container", self._name)

        for callback in self._subscribers:
            callback(remove=True)

        self._subscriber = []

    #############################################################
    async def _start(self):
        """Separate loop to start container, because HA loop can't be used."""

        try:
            await self._container.start()
        except Exception as err:
            _LOGGER.error("%s: Can not start containner (%s)", self._name, str(err))
        finally:
            self._busy = False

    #############################################################
    async def start(self):
        """Called from HA switch."""
        _LOGGER.info("%s: Start container", self._name)

        self._busy = True
        self._loop.create_task(self._start())

    #############################################################
    async def _stop(self):
        """Separate loop to stop container, because HA loop can't be used."""
        try:
            await self._container.stop(t=10)
        except Exception as err:
            _LOGGER.error("%s: Can not stop containner (%s)", self._name, str(err))
        finally:
            self._busy = False

    #############################################################
    async def stop(self):
        """Called from HA switch."""
        _LOGGER.info("%s: Stop container", self._name)

        self._busy = True
        self._loop.create_task(self._stop())

    #############################################################
    def get_name(self):
        """Return the container name."""
        return self._name

    #############################################################
    def get_info(self):
        """Return the container info."""
        return self._info

    #############################################################
    def get_stats(self):
        """Return the container stats."""
        return self._stats

    #############################################################
    def register_callback(self, callback, variable):
        """Register callback from sensor/switch."""
        if callback not in self._subscribers:
            _LOGGER.debug(
                "%s: Added callback to container, entity: %s", self._name, variable
            )
            self._subscribers.append(callback)

    #############################################################
    def _notify(self):
        if len(self._subscribers) > 0:
            _LOGGER.debug(
                "%s: Send notify (%d) to container", self._name, len(self._subscribers)
            )

        for callback in self._subscribers:
            callback()

    #############################################################
    @staticmethod
    def _calcdockerformat(dt):
        """Calculate datetime to Docker format, because it isn't available in stats."""
        if dt is None:
            return "None"

        delta = relativedelta.relativedelta(datetime.now(timezone.utc), dt)

        if delta.years != 0:
            return "{} {}".format(delta.years, "year" if delta.years == 1 else "years")
        elif delta.months != 0:
            return "{} {}".format(
                delta.months, "month" if delta.months == 1 else "months"
            )
        elif delta.days != 0:
            return "{} {}".format(delta.days, "day" if delta.days == 1 else "days")
        elif delta.hours != 0:
            return "{} {}".format(delta.hours, "hour" if delta.hours == 1 else "hours")
        elif delta.minutes != 0:
            return "{} {}".format(
                delta.minutes, "minute" if delta.minutes == 1 else "minutes"
            )

        return "{} {}".format(
            delta.seconds, "second" if delta.seconds == 1 else "seconds"
        )
