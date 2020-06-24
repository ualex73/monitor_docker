# Custom Monitor Docker component for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Default-orange.svg?style=for-the-badge)](https://github.com/custom-components/hacs)

## About

This repository contains the Monitor Docker component I developed for monitoring my Docker environment from [Home-Assistant](https://www.home-assistant.io). It is inspired by the Sander Huisman [Docker Monitor](https://github.com/Sanderhuisman/docker_monitor), where I switched mainly from threads to asyncio and put my own wishes/functionality in.  Feel free to use the component and report bugs if you find them. If you want to contribute, please report a bug or pull request and I will reply as soon as possible.

## Monitor Docker

The Monitor Docker allows you to monitor Docker and container statistics and turn on/off containers. It can connected to the Docker daemon locally or remotely. When Home Assistant is used within a Docker container, the Docker daemon should be mounted as follows `-v /var/run/docker.sock:/var/run/docker.sock`.

**Docker run Example**
```
docker run -d \
... \
-v /var/run/docker.sock:/var/run/docker.sock \
  homeassistant/home-assistant
```

**docker-compose.yaml Example**
```
services:
  hass:
    image: homeassistant/home-assistant
...
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
...
```
**NOTE:** Making `/var/run/docker.sock` read-only has no effect, because it is a socket (and not file).

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
| url                  | string       (Optional)  | Host URL of Docker daemon. Defaults to `unix://var/run/docker.sock`. Remote Docker daemon via TCP socket is also supported, use e.g. `tcp://ip:2376/`. For TLS support see Q&A section. |
| scan_interval        | time_period  (Optional)  | Update interval. Defaults to 10 seconds.                              |
| certpath             | string       (Optional)  | If TCP socket is used, you can define your Docker certificate path, forcing Monitor Docker to enable TLS.|
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
| containers_paused                 | Number of paused containers     | -     |
| containers_stopped                | Number of stopped containers    | -     |
| containers_cpu_percentage         | CPU Usage                       | %     |
| containers_memory                 | Memory usage                    | MB    |
| containers_memory_percentage      | Memory usage                    | %     |
| images                            | Number of images                | -     |
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

It is possible to debug the Monitor Docker component, this can be done by adding the following lines to the `configuration.yaml` file:

```yaml
logger:
  logs:
    custom_components.monitor_docker: debug
```

### Q&A
Here are some possible questions/errors with their answers.

1. **Question:** Does this integration work with the HASS or supervisord installers?  
    **Answer:** Most likely not, because they don't expose the Docker UNIX/TCP socket. If you got it working, please let me know, then I can add it to the README
1. **Error:** `Missing valid docker_host.Either DOCKER_HOST or local sockets are not available.`  
    **Answer:** Most likely the socket is not mounted properly in your Home Assistant container. Please check if you added the volume `/var/run/docker.sock`
1. **Error:** `aiodocker.exceptions.DockerError: DockerError(900, "Cannot connect to Docker Engine via tcp://10.0.0.1:2376/...)`. 
    **Answer:** You are trying to connect via TCP and most likely the remote address is unavailable. Test it with the command `docker -H tcp://10.0.0.1:2376 ps` if it works (ofcourse replace `10.0.0.1` with your IP address)
1. **Question** Is Docker TCP socket via TLS supported?  
    **Answer:** Yes it is. You need to set the url to e.g. `tcp://ip:2376` and the environment variables `DOCKER_TLS_VERIFY=1` and `DOCKER_CERT_PATH=<path to your certificates>` need to be set
1. **Question:** Can this integration monitor 2 or more Docker instances?  
    **Answer:** Yes it can. Just duplicate the entries and give it an unique name and define the url as shown below:
```yaml
# Example configuration.yaml entry
monitor_docker:
  - name: Docker
    containers:
    ...
  - name: RemoteDocker
    url: tcp://10.0.0.1:2376
    containers:
    ...
```

## Credits

* [Sanderhuisman](https://github.com/Sanderhuisman/docker_monitor)

## License

Apache License 2.0
