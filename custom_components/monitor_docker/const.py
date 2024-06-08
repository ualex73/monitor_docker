"""Define constants for the Monitor Docker component."""

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import PERCENTAGE, UnitOfDataRate, UnitOfInformation

DOMAIN = "monitor_docker"
API = "api"
CONFIG = "config"
CONTAINER = "container"

CONF_CERTPATH = "certpath"
CONF_CONTAINERS = "containers"
CONF_CONTAINERS_EXCLUDE = "containers_exclude"
CONF_MEMORYCHANGE = "memorychange"
CONF_PRECISION_CPU = "precision_cpu"
CONF_PRECISION_MEMORY_MB = "precision_memory_mb"
CONF_PRECISION_MEMORY_PERCENTAGE = "precision_memory_percentage"
CONF_PRECISION_NETWORK_KB = "precision_network_kb"
CONF_PRECISION_NETWORK_MB = "precision_network_mb"
CONF_PREFIX = "prefix"
CONF_RENAME = "rename"
CONF_RENAME_ENITITY = "rename_entity"
CONF_RETRY = "retry"
CONF_SENSORNAME = "sensorname"
CONF_SWITCHENABLED = "switchenabled"
CONF_SWITCHNAME = "switchname"
CONF_BUTTONENABLED = "buttonenabled"
CONF_BUTTONNAME = "buttonname"

DEFAULT_NAME = "Docker"
DEFAULT_RETRY = 60
DEFAULT_SENSORNAME = "{name} {sensor}"
DEFAULT_SWITCHNAME = "{name}"
DEFAULT_BUTTONNAME = "{name} Restart"

COMPONENTS = ["sensor", "switch", "button"]

SERVICE_RESTART = "restart"

PRECISION = 2

DOCKER_INFO_VERSION = "version"
DOCKER_INFO_CONTAINER_RUNNING = "containers_running"
DOCKER_INFO_CONTAINER_PAUSED = "containers_paused"
DOCKER_INFO_CONTAINER_STOPPED = "containers_stopped"
DOCKER_INFO_CONTAINER_TOTAL = "containers_total"
DOCKER_INFO_IMAGES = "images"
DOCKER_STATS_CPU_PERCENTAGE = "containers_cpu_percentage"
DOCKER_STATS_1CPU_PERCENTAGE = "containers_1cpu_percentage"
DOCKER_STATS_MEMORY = "containers_memory"
DOCKER_STATS_MEMORY_PERCENTAGE = "containers_memory_percentage"

CONTAINER_INFO_ALLINONE = "allinone"
CONTAINER_INFO_STATE = "state"
CONTAINER_INFO_HEALTH = "health"
CONTAINER_INFO_STATUS = "status"
CONTAINER_INFO_NETWORK_AVAILABLE = "network_available"
CONTAINER_INFO_UPTIME = "uptime"
CONTAINER_INFO_IMAGE = "image"
CONTAINER_STATS_CPU_PERCENTAGE = "cpu_percentage"
CONTAINER_STATS_1CPU_PERCENTAGE = "1cpu_percentage"
CONTAINER_STATS_MEMORY = "memory"
CONTAINER_STATS_MEMORY_PERCENTAGE = "memory_percentage"
CONTAINER_STATS_NETWORK_SPEED_UP = "network_speed_up"
CONTAINER_STATS_NETWORK_SPEED_DOWN = "network_speed_down"
CONTAINER_STATS_NETWORK_TOTAL_UP = "network_total_up"
CONTAINER_STATS_NETWORK_TOTAL_DOWN = "network_total_down"

DOCKER_MONITOR_LIST = {
    DOCKER_INFO_VERSION: SensorEntityDescription(
        key=DOCKER_INFO_VERSION,
        name="Version",
        icon="mdi:information-outline",
    ),
    DOCKER_INFO_CONTAINER_RUNNING: SensorEntityDescription(
        key=DOCKER_INFO_CONTAINER_RUNNING,
        name="Containers Running",
        icon="mdi:docker",
    ),
    DOCKER_INFO_CONTAINER_PAUSED: SensorEntityDescription(
        key=DOCKER_INFO_CONTAINER_PAUSED,
        name="Containers Paused",
        icon="mdi:docker",
    ),
    DOCKER_INFO_CONTAINER_STOPPED: SensorEntityDescription(
        key=DOCKER_INFO_CONTAINER_STOPPED,
        name="Containers Stopped",
        icon="mdi:docker",
    ),
    DOCKER_INFO_CONTAINER_TOTAL: SensorEntityDescription(
        key=DOCKER_INFO_CONTAINER_TOTAL,
        name="Containers Total",
        icon="mdi:docker",
    ),
    DOCKER_STATS_CPU_PERCENTAGE: SensorEntityDescription(
        key=DOCKER_STATS_CPU_PERCENTAGE,
        name="CPU",
        native_unit_of_measurement=PERCENTAGE,
        icon="mdi:chip",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    DOCKER_STATS_1CPU_PERCENTAGE: SensorEntityDescription(
        key=DOCKER_STATS_1CPU_PERCENTAGE,
        name="1CPU",
        native_unit_of_measurement=PERCENTAGE,
        icon="mdi:chip",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    DOCKER_STATS_MEMORY: SensorEntityDescription(
        key=DOCKER_STATS_MEMORY,
        name="Memory",
        native_unit_of_measurement=UnitOfInformation.MEBIBYTES,
        icon="mdi:memory",
        device_class=SensorDeviceClass.DATA_SIZE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    DOCKER_STATS_MEMORY_PERCENTAGE: SensorEntityDescription(
        key=DOCKER_STATS_MEMORY_PERCENTAGE,
        name="Memory (percent)",
        native_unit_of_measurement=PERCENTAGE,
        icon="mdi:memory",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    DOCKER_INFO_IMAGES: SensorEntityDescription(
        key=DOCKER_INFO_IMAGES,
        name="Images",
        icon="mdi:docker",
    ),
}

CONTAINER_MONITOR_LIST = {
    CONTAINER_INFO_STATE: SensorEntityDescription(
        key=CONTAINER_INFO_STATE,
        name="State",
        icon="mdi:checkbox-marked-circle-outline",
    ),
    CONTAINER_INFO_HEALTH: SensorEntityDescription(
        key=CONTAINER_INFO_HEALTH,
        name="Health",
        icon="mdi:heart-pulse",
    ),
    CONTAINER_INFO_STATUS: SensorEntityDescription(
        key=CONTAINER_INFO_STATUS,
        name="Status",
        icon="mdi:checkbox-marked-circle-outline",
    ),
    CONTAINER_INFO_UPTIME: SensorEntityDescription(
        key=CONTAINER_INFO_UPTIME,
        name="Up Time",
        icon="mdi:clock",
        device_class=SensorDeviceClass.TIMESTAMP,
    ),
    CONTAINER_INFO_IMAGE: SensorEntityDescription(
        key=CONTAINER_INFO_IMAGE,
        name="Image",
        icon="mdi:information-outline",
    ),
    CONTAINER_STATS_CPU_PERCENTAGE: SensorEntityDescription(
        key=CONTAINER_STATS_CPU_PERCENTAGE,
        name="CPU",
        native_unit_of_measurement=PERCENTAGE,
        icon="mdi:chip",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    CONTAINER_STATS_1CPU_PERCENTAGE: SensorEntityDescription(
        key=CONTAINER_STATS_1CPU_PERCENTAGE,
        name="1CPU",
        native_unit_of_measurement=PERCENTAGE,
        icon="mdi:chip",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    CONTAINER_STATS_MEMORY: SensorEntityDescription(
        key=CONTAINER_STATS_MEMORY,
        name="Memory",
        native_unit_of_measurement=UnitOfInformation.MEBIBYTES,
        icon="mdi:memory",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    CONTAINER_STATS_MEMORY_PERCENTAGE: SensorEntityDescription(
        key=CONTAINER_STATS_MEMORY_PERCENTAGE,
        name="Memory (percent)",
        native_unit_of_measurement=PERCENTAGE,
        icon="mdi:memory",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    CONTAINER_STATS_NETWORK_SPEED_UP: SensorEntityDescription(
        key=CONTAINER_STATS_NETWORK_SPEED_UP,
        name="Network speed Up",
        native_unit_of_measurement=UnitOfDataRate.KIBIBYTES_PER_SECOND,
        icon="mdi:upload",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    CONTAINER_STATS_NETWORK_SPEED_DOWN: SensorEntityDescription(
        key=CONTAINER_STATS_NETWORK_SPEED_DOWN,
        name="Network speed Down",
        native_unit_of_measurement=UnitOfDataRate.KIBIBYTES_PER_SECOND,
        icon="mdi:download",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    CONTAINER_STATS_NETWORK_TOTAL_UP: SensorEntityDescription(
        key=CONTAINER_STATS_NETWORK_TOTAL_UP,
        name="Network total Up",
        native_unit_of_measurement=UnitOfInformation.MEBIBYTES,
        icon="mdi:upload",
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    CONTAINER_STATS_NETWORK_TOTAL_DOWN: SensorEntityDescription(
        key=CONTAINER_STATS_NETWORK_TOTAL_DOWN,
        name="Network total Down",
        native_unit_of_measurement=UnitOfInformation.MEBIBYTES,
        icon="mdi:download",
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    CONTAINER_INFO_ALLINONE: SensorEntityDescription(
        key=CONTAINER_INFO_ALLINONE,
        name="State",
        icon="mdi:checkbox-marked-circle-outline",
    ),
}

CONTAINER_MONITOR_NETWORK_LIST = [
    CONTAINER_STATS_NETWORK_SPEED_UP,
    CONTAINER_STATS_NETWORK_SPEED_DOWN,
    CONTAINER_STATS_NETWORK_TOTAL_UP,
    CONTAINER_STATS_NETWORK_TOTAL_DOWN,
]

MONITORED_CONDITIONS_LIST = list(DOCKER_MONITOR_LIST.keys()) + list(
    CONTAINER_MONITOR_LIST.keys()
)

ATTR_NAME = "name"
ATTR_MEMORY_LIMIT = "Memory_limit"
ATTR_ONLINE_CPUS = "Online_CPUs"
ATTR_SERVER = "server"
ATTR_VERSION_ARCH = "Architecture"
ATTR_VERSION_KERNEL = "Kernel"
ATTR_VERSION_OS = "OS"
ATTR_VERSION_OS_TYPE = "OS_Type"
