# DS18B20 1-Wire temperature sensor to MQTT gateway for Home Assistant

Inspired by a [Waveshare Raspberry Pi 1-Wire DS18B20 Tutorial][waveshare_tutorial], combined with my work on [DAVe3283/rtl_433-to-mqtt-for-hass]. Publishes all detected DS18B20 sensors on the 1-Wire bus to Home Assistant.

Only tested on a Raspberry Pi 2 Model B Rev 1.1 running Raspbian 10 (buster) May 2020.

# Configuration

To use this tool, you need to create the configuration file `config.py`:

```py
# MQTT Configuration
MQTT_USER="user"
MQTT_PASS="password"
MQTT_HOST="host.fqdn or ip"
MQTT_TLS=False
MQTT_PORT=1883 # 8883 for TLS
MQTT_ROOT_CA="" # Leave blank to use system CA store, or provide the path to an internal CA or cert
MQTT_QOS=0

# When run as a service, sometimes the script will start before DNS is available
# Instead of crashing, retry once a second this many times before giving up
CONNECTION_ATTEMPTS=60

UPDATE_INTERVAL=30 # seconds
CONFIG_INTERVAL=10 # minutes
DEBUG=False
```

## MQTT with TLS

It is recommended to use MQTT over TLS where possible, especially over the public Internet. To secure the connection, the server's certificate needs to be verified by the client.

* If your MQTT server has a commercial certificate from a recognized Certificate Authority (CA), no special client configuration is necessary!
* If your server uses a self-signed certificate, you will need a copy of the server's public cert, and update `MQTT_ROOT_CA` in `config.py` with the path to the public cert.
* If you have an internal CA, you can set `MQTT_ROOT_CA`, but the recommended method is to add the root CA to the operating system's CA store.

### Add a root CA to the OS CA store

For example, in Debian 10 (stretch):

```bash
# Create directory for your domain
sudo mkdir /usr/local/share/ca-certificates/your.domain

# Get root CA from a webserver. Could also rsync it over, etc.
sudo wget -P /usr/local/share/ca-certificates/your.domain http://www.your.domain/pki/root.crt
# Repeat for any other/intermediate certs to trust (not usually needed)

# Refresh the OS CA store
sudo update-ca-certificates
```

# Prerequisites

## Python 3 & [pip]

Virtually every Linux distribution has Python 3, either pre-installed, or as a package.
We also need [pip] to support a later dependency.

```bash
sudo apt install python3 python3-pip
```

## [paho-mqtt]

Use `pip` to install `paho-mqtt` for the current user.
(If you are going to run the service as a different user, install `paho-mqtt` for that user instead.)

```bash
pip3 install paho-mqtt
```

# Installation

The script will be configured to run as a service, so the machine can be rebooted without requiring any interaction to get the gateway working again.

It can run as a different user, but it is easier to just use your normal user account.
(Pull requests welcome to add instructions for running the service as a different user.)

First, edit the `ds18b20-to-mqtt.service` file.
* Update `User=your_username` with the correct username.
* Update `ExecStart=/usr/bin/python3 /home/your_username/ds18b20-to-mqtt-for-hass/ds18b20-mqtt-bridge.py` with the correct path to this repository

Now, add the service:

```bash
sudo cp ds18b20-to-mqtt.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable ds18b20-to-mqtt.service
sudo service ds18b20-to-mqtt start
```

# Configuration changes

If any changes are made to `config.py`, the service will need restarted to apply them.

```bash
sudo service ds18b20-to-mqtt restart
```

[DAVe3283/rtl_433-to-mqtt-for-hass]: https://github.com/DAVe3283/rtl_433-to-mqtt-for-hass
[paho-mqtt]: https://pypi.org/project/paho-mqtt/
[pip]: https://pip.pypa.io/en/stable/
[waveshare_tutorial]: https://www.waveshare.com/wiki/Raspberry_Pi_Tutorial_Series:_1-Wire_DS18B20_Sensor
