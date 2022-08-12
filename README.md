# Raspberry Electrical Panel

Raspberry Pi used as a connected electrical panel for the Green Home Lan project.
The [RLB0665N 6CH Relay board](http://osaelectronics.com/get/raspberry/automation/RLB0665N/RLB0665N_datasheet.pdf) is controled by the raspberry pi via GPIO I2C.

* The Raspberry runs an MQTT broker
* The ***command/relay*** topic is used to publish commands to control the connected electrical panel.
* The ***status/relay*** topic is used by the rpi-electrical-panel to publish periodically the relays states.

## **Raspberry OS setup**

Download the last version of the Bullseye Raspberri PI OS and flash it to the SD card.
You can use the [Raspberry Pi imager](https://www.raspberrypi.com/software/) to download and flash the OS.

1. Activate the SSH, I2S and configure the localisation and WLAN options

```bash
sudo raspi-config
```

* Activate SSH and I2C (Interface Options)
* Configure timezone (Localization Options -> Timezone)
* Configure WLAN country to enable wlan0 interface (Localization Options -> WLAN Country)

A reboot is necessary to take into account the modifications

```bash
sudo reboot now
```

As of now, the screen and keyboard are no longer useful. You can connect to the raspberry via SSH

2. Keyboard configurations (Only for FR keyboards layout)

```bash
sudo nano /etc/default/keyboard
```

modify the line *XKBLAYOUT="gb"* par *XKBLAYOUT="fr"*

In order to stop receiving environment variables from the SSH client you have to modify the ssh configuration file:

```bash
sudo nano /etc/ssh/sshd_config
```

 Comment the line *`AcceptEnv LANG LC_*`*

## **MQTT Broker setup**

This project uses a mosquitto MQTT broker.

**Step-1**
Update the RPI OS

```bash
sudo apt-get update
sudo apt-get upgrade
sudo apt-get dist-upgrade
```

**Step-2**
Install mosquitto and then the mosquitto-clients packages.

```bash
sudo apt-get install mosquitto -y
sudo apt-get install mosquitto-clients -y
```

**Step-3**
Configure the MQTT broker. The Mosquitto broker’s configuration file is located at */etc/mosquitto/mosquitto.conf*

```bash
sudo nano /etc/mosquitto/mosquitto.conf
```

Replace the line *include_dir /etc/mosquitto/conf.d* by :

```
allow_anonymous true
listener 1883
```

A reboot is necessary to take into account the modifications

```bash
sudo reboot now
```

**Step-4**
Test de MQTT broker by using the *mosquito_sub* and *mosquito_pub* commands (run commands in separated terminals)

```bash
mosquitto_sub -d -u username -P password -t test
```

```bash
mosquitto_pub -d -u username -P password -t test -m "Hello, World!"
```

## **Run the rpi-electrical-panel application**

### **1. Install dependencies**

Install the project dependencies in a virtual environement

To install the dependencies manager [poetry](https://python-poetry.org/)

```bash
 curl -sSL https://raw.githubusercontent.com/python-poetry/poetry/master/get-poetry.py | python -
```

Configure poetry to create virtual environments in the project directory

```bash
poetry config virtualenvs.in-project true
```

Install dependencies and activate the virtual environment:

```bash
poetry install
poetry shell
```

### **2. Create logfiles**

Log files defined in configuration file located in *server/config/logging-config.yml* must be created before launching the application

```bash
mkdir logs
touch logs/mqtt.log
touch api-rest.log
```

### **3. Set env vars**

Define the flask environment variables:

TODO:double check vars

```bash
export FLASK_APP="server/app:create_app()"
export FLASK_ENV=production
```

### **4. Run the flask application**

Run the application

```bash
flask run
```

**You can run the application via VS Code running the `RPI Electrical Panel` configuration**

## **Testing scripts**

The test scripts are located in *test_scripts/*
These scripts must be launched from a dev pc connected to the network where the raspberry-electrical-panel is located. Dependencies install is necessary.

(set the *HOST* variable in the test scripts as the RPI ip address)

**mqtt_publisher_test.py** -> publish messages periodically to the topic *command/relays* to change relays status

```bash
python test_scripts/mqtt_publisher_test.py
```

**mqtt_subscriber_test.py** -> subscribe to the topic *command/relays* to receive relays status change messages

```bash
python test_scripts/mqtt_subscriber_test.py

```

## TODO LIST

* [ ] DEfine logs rotation policy
* [ ] MQTT Messages model as external lib
* [X] MQTT reconnection procedure
* [ ] Methods docs
* [ ] Relays status -> state
* [ ] Errors handle
* [ ] Time params to conf
* [ ] Explain MQTT broker and topics in doc (Confluence ?)
* [ ] Explain MQTT messages in doc (Confluence ?)
