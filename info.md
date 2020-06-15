# Custom Monitor Docker component for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Default-orange.svg?style=for-the-badge)](https://github.com/custom-components/hacs)

## About

This repository contains the Monitor Docker component I developed for monitoring my Docker environment from [Home-Assistant](https://www.home-assistant.io). It is inspired by the Sander Huismans [Docker Monitor](https://github.com/Sanderhuisman/docker_monitor), where I switched mainly from threads to asyncio and put my own wishes/functionality in.  Feel free to use the component and report bugs if you find them. If you want to contribute, please report a bug or pull request and I will reply as soon as possible.

## Monitor Docker

The Monitor Docker allows you to monitor Docker and container statistics and turn on/off containers. It can connected to the Docker daemon locally or remotely. When Home Assistant is used within a Docker container, the Docker daemon should be mounted as follows `-v /var/run/docker.sock:/var/run/docker.sock`.

### Configuration

To use the `monitor_docker` in your installation, add the following to your `configuration.yaml` file:

```yaml
# Example configuration.yaml entry
monitor_docker:
  - name: Docker
    containers:
      - appdaemon
      - db-dsmr
      - db-hass
      - deconz
      - dsmr
      - hass
      - influxdb
      - mosquitto
      - nodered
      - unifi
    rename:
      appdaemon: AppDaemon
      db-dsmr: "Database DSMR-Reader"
      db-hass: Database Home Assistant
      deconz: DeCONZ
      dsmr: "DSMR-Reader"
      hass: Home Assistant
      influxdb: InfluxDB
      mosquitto: Mosquitto
      nodered: "Node-RED"
      unifi: UniFi
    monitored_conditions:
      - version
      - containers_running
      - containers_total
      - status
      - memory
```

#### Configuration variables

| Parameter            | Type                     | Description                                                           |
| -------------------- | ------------------------ | --------------------------------------------------------------------- |
| name                 | string       (Required)  | Client name of Docker daemon. Defaults to `Docker`.                   |
| url                  | string       (Optional)  | Host URL of Docker daemon. Defaults to `unix://var/run/docker.sock`.  |
| scan_interval        | time_period  (Optional)  | Update interval. Defaults to 10 seconds.                              |
| containers           | list         (Optional)  | Array of containers to monitor. Defaults to all containers.           |
| monitored_conditions | list         (Optional)  | Array of conditions to be monitored. Defaults to all conditions.      |
| rename               | dictionary   (Optional)  | Dictionary of containers to rename. Default no renaming.              |
| sensorname           | string       (Optional)  | Sensor string to format the name used in Home Assistant. Defaults to `{name} {sensor}`, where `{name}` is the container name and `{sensor}` is e.g. Memory, Status, Network speed Up |
| switchname           | string       (optional)  | Switch string to format the name used in Home Assistant. Defaults to `{name}`, where `{name}` is the container name. |

| Monitored Conditions              | Description                     | Unit  |
| --------------------------------- | ------------------------------- | ----- |
| version                           | Docker version                  | -     |
| containers_total                  | Total number of containers      | -     |
| containers_running                | Number of running containers    | -     |
| containers_cpu_percentage         | CPU Usage                       | %     |
| containers_memory                 | Memory usage                    | MB    |
| containers_memory_percentage      | Memory usage                    | %     |
| status                            | Container status                | -     |
| uptime                            | Container start time            | -     |
| image                             | Container image                 | -     |
| cpu_percentage                    | CPU usage                       | %     |
| memory                            | Memory usage                    | MB    |
| memory_percentage                 | Memory usage                    | %     |
| network_speed_up                  | Network speed upstream          | kB/s  |
| network_speed_down                | Network speed downstream        | kB/s  |
| network_total_up                  | Network total upstream          | MB    |
| network_total_down                | Network total downstream        | MB    |

### Debugging

It is possible to debug the Monito Docker component, this can be done by adding the following lines to the `configuration.yaml` file:

```yaml
logger:
  logs:
    custom_components.monitor_docker: debug
```

## Credits

* [Sanderhuisman](https://github.com/Sanderhuisman/docker_monitor)

## License

Apache License 2.0
