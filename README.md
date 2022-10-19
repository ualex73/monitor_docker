# Custom Monitor Docker component for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Default-orange.svg?style=for-the-badge)](https://github.com/hacs/integration)

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
NOTE: Making `/var/run/docker.sock` read-only has no effect, because it is a socket (and not file).

**Raspberry Pi (Raspbian)**

Using a Raspberry Pi with Raspbian it could happen no memory is reported. In such case the Docker API does not report it to Monitor Docker. Making the following changes, normally fixes the problem:
- Open the file `/boot/cmdline.txt`
- Add the following to the end of the existing line `cgroup_enable=cpuset cgroup_memory=1 cgroup_enable=memory`
- Reboot your Raspberry Pi

NOTE: Add the line to the existing line, do *not* replace it

**Ubuntu / Debian**

Also on Ubuntu/Debian it is possible no memory is shown, the following changes could solve your problem:
- Open the file `/etc/default/grub`
- Modify the `GRUB_CMDLINE_LINUX_DEFAULT=""` to `GRUB_CMDLINE_LINUX_DEFAULT="quiet cgroup_enable=memory swapaccount=1"`
- Run `sudo update-grub`
- Reboot your Ubuntu/Debian

NOTE: This is untested, use at your risk

## Installation

### HACS - Recommended
- Have [HACS](https://hacs.xyz) installed, this will allow you to easily manage and track updates.
- Search for 'Monitor Docker'.
- Click Install below the found integration.
- Configure using the configuration instructions below.
- If applicable, add the volume `/var/run/docker.sock` to your Home Assistant container.
- Restart Home-Assistant.

### Manual
- Copy directory `custom_components/monitor_docker` to your `<config dir>/custom_components` directory.
- Configure with config below.
- If applicable, add the volume `/var/run/docker.sock` to your Home Assistant container.
- Restart Home-Assistant.

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
      - state
      - status
      - memory
```

#### Configuration variables

| Parameter                   | Type                     | Description                                                           |
| --------------------------- | ------------------------ | --------------------------------------------------------------------- |
| name                        | string       (Required)  | Client name of Docker daemon. Defaults to `Docker`.                   |
| url                         | string       (Optional)  | Host URL of Docker daemon. Defaults to `unix://var/run/docker.sock`. Remote Docker daemon via TCP socket is also supported, use e.g. `tcp://ip:2376`. Do NOT add a slash add the end, this will invalid the URL. For TLS support see Q&A section. SSH is not supported. |
| scan_interval               | time_period  (Optional)  | Update interval. Defaults to 10 seconds.                              |
| certpath                    | string       (Optional)  | If TCP socket is used, you can define your Docker certificate path, forcing Monitor Docker to enable TLS. The filenames must be `cert.pem` and `key.pem`|
| containers                  | list         (Optional)  | Array of containers to monitor. Defaults to all containers.           |
| containers_exclude          | list         (Optional)  | Array of containers to be excluded from monitoring, when all containrs are included. |
| monitored_conditions        | list         (Optional)  | Array of conditions to be monitored. Defaults to all conditions.      |
| rename                      | dictionary   (Optional)  | Dictionary of containers to rename. Default no renaming.              |
| sensorname                  | string       (Optional)  | Sensor string to format the name used in Home Assistant. Defaults to `{name} {sensor}`, where `{name}` is the container name and `{sensor}` is e.g. Memory, Status, Network speed Up |
| switchname                  | string       (Optional)  | Switch string to format the name used in Home Assistant. Defaults to `{name}`, where `{name}` is the container name. |
| switchenabled               | boolean      (Optional)  | Enable/Disable the switch entity for all container (Default: enabled) |
| precision_cpu               | integer      (Optional)  | Precision of CPU usage percentage (Default: 2) |
| precision_memory_mb         | integer      (Optional)  | Precision of memory usage in MB (Default: 2) |
| precision_memory_percentage | integer      (Optional)  | Precision of memory usage in percentage (Default: 2) |
| precision_network_kb        | integer      (Optional)  | Precision of network bandwidth in kB (Default: 2) |
| precision_network_mb        | integer      (Optional)  | Precision of network usage in MB (Default: 2) |

| Monitored Conditions              | Description                     | Unit  |
| --------------------------------- | ------------------------------- | ----- |
| version                           | Docker version                  | -     |
| containers_total                  | Total number of containers      | -     |
| containers_running                | Number of running containers    | -     |
| containers_paused                 | Number of paused containers     | -     |
| containers_stopped                | Number of stopped containers    | -     |
| containers_cpu_percentage         | CPU Usage. The CPU usage depends on the number of CPU cores, e.g. if you have 8 cores, this value can have a maximum of 800% | %     |
| containers_1cpu_percentage        | CPU Usage, between 0-100%       | %     |
| containers_memory                 | Memory usage                    | MB    |
| containers_memory_percentage      | Memory usage                    | %     |
| images                            | Number of images                | -     |
| state                             | Container state. This is created, restarting, running, removing, paused, exited or dead  | -     |
| status                            | Container status. E.g. Up 13 days, Up 5 hours, Exited (0) 11 hours ago | -     |
| health                            | Container health if available   | -     |
| uptime                            | Container start time            | -     |
| image                             | Container image                 | -     |
| cpu_percentage                    | CPU usage. The CPU usage depends on the number of CPU cores, e.g. if you have 8 cores, this value can have a maximum of 800% | %     |
| 1cpu_percentage                   | CPU Usage, between 0-100%       | %     |
| memory                            | Memory usage                    | MB    |
| memory_percentage                 | Memory usage                    | %     |
| network_speed_up                  | Network speed upstream          | kB/s  |
| network_speed_down                | Network speed downstream        | kB/s  |
| network_total_up                  | Network total upstream          | MB    |
| network_total_down                | Network total downstream        | MB    |
| allinone                          | This is a special condition and when used, it will only create 1 sensor per container with all the monitored conditions as attribute value |-     |

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
    **Answer:** Yes, with an external docker container. Home Assistant supervised does not expose the Docker UNIX/TCP socket. However, you can use an external docker container named `docker-socket-proxy`. Start this docker with the following docker-compose code. It exposes the socket over TCP and `monitor_docer` can listen to it.
    ```yaml
    # Proxy the Docker sock so that we can pick up stats for HomeAssistant
    dockerproxy:
      image: tecnativa/docker-socket-proxy
      container_name: dockerproxy
      privileged: true
      volumes:
        - /var/run/docker.sock:/var/run/docker.sock
      ports:
        - 2375:2375
      environment:
        - BUILD=1
        - COMMIT=1
        - CONFIGS=1
        - CONTAINERS=1
        - DISTRIBUTION=1
        - EXEC=1
        - IMAGES=1
        - INFO=1
        - NETWORKS=1
        - NODES=1
        - PLUGINS=1
        - SERVICES=1
        - SESSSION=1
        - SWARM=1
        - POST=1
    ```
    Add the following to your `configuration.yaml`:
```yaml
    monitor_docker:
      - name: Docker
        url: tcp://<host_ip>:2375
```
2. **Error:** `Missing valid docker_host.Either DOCKER_HOST or local sockets are not available.`  
    **Answer:** Most likely the socket is not mounted properly in your Home Assistant container. Please check if you added the volume `/var/run/docker.sock`
3. **Error:** `aiodocker.exceptions.DockerError: DockerError(900, "Cannot connect to Docker Engine via tcp://10.0.0.1:2376...)`.  
    **Answer:** You are trying to connect via TCP and most likely the remote address is unavailable. Test it with the command `docker -H tcp://10.0.0.1:2376 ps` if it works (ofcourse replace `10.0.0.1` with your IP address)
4. **Question:** Is Docker TCP socket via TLS supported?  
    **Answer:** Yes it is. You need to set the url to e.g. `tcp://ip:2376` and the environment variables `DOCKER_TLS_VERIFY=1` and `DOCKER_CERT_PATH=<path to your certificates>` need to be set  
The following is a docker-compose example how to set the environment variables and the volume with the certificates:
```
services:
  hass:
    image: homeassistant/home-assistant
...
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
      # The files need to be named "cert.pem" and "key.pem"
      - ./certs:/certs
    environment:
      - DOCKER_TLS_VERIFY=1
      - DOCKER_CERT_PATH=/certs
...
```
5. **Question:** Can this integration monitor 2 or more Docker instances?  
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
*NOTE*: The integration supports multiple Docker instances, but you can only define 1 TLS configuration which is applied to all (thus you cannot mix TCP with and without TLS).  
6. **Question:** Can create, delete or re-create of a container be implemented in the integration?  
    **Answer:** The used Docker library has no easy (and safe) way to handle such functionality. Please use *docker-compose* to handle such operations. If anybody can make this fully and safe working, I am happy to merge the PR   
7. **Question:** Can you add more security to a switch?  
    **Answer:** No, this isn't possible from the integration. You need to do this directly in Lovelace itself, with the card e.g. https://github.com/iantrich/restriction-card  
8. **Question:** All the report memories values are 0 (zero), can this be fixed in the integration?  
    **Answer:** No, the integration just uses the available information from the API and you should fix your Docker   
9. **Question:** It is possible to monitor HASS.IO?  
    **Answer:** Yes, please use the Docker Socker Proxy https://github.com/Tecnativa/docker-socket-proxy and configure tcp://ip:port to connect to the proxy. This has been tested and verified by other users, but I cannot give support on it.   
10. **Question:** I get a permission denied error?  
     **Answer:** In general Docker and HASS.IO are running as root and always can connect to /var/run/docker.sock. If you run in a venv environment or directly with Python, you may need to add "docker" to the user used for Home Assistant. The following commands may help you, and it is recommended to reboot after "usermod":
  ```
  $ sudo usermod -a -G docker <user>
  $ sudo reboot
  ```  
11. **Question:** Can you add the feature to check if images are update in e.g. hub.docker.com?  
     **Answer:** Such feature goes outside of the scope of monitor_docker and there are few other options available for this. You can use https://newreleases.io or https://github.com/crazy-max/diun/    
12. **Question:** Is Docker via SSH supported?  
     **Answer:** No, the Docker library used, does not support it. There is a small _but_, maybe you can get it to work via `socat`. The following URL may help you: https://serverfault.com/questions/127794/forward-local-port-or-socket-file-to-remote-socket-file/362833#362833

## Credits

* [Sanderhuisman](https://github.com/Sanderhuisman/docker_monitor)

## License

Apache License 2.0
