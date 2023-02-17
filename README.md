# Raspberry Electrical Panel

Raspberry Pi used as a connected electrical panel for the Green Home Lan project.
The [RLB0665N 6CH Relay board](http://osaelectronics.com/get/raspberry/automation/RLB0665N/RLB0665N_datasheet.pdf) is controled by the raspberry pi via GPIO I2C.

* The Raspberry runs an MQTT broker
* The ***command/relay*** topic is used to publish commands to control the connected electrical panel.
* The ***status/relay*** topic is used by the rpi-electrical-panel to publish periodically the relays states.

## **Raspberry OS setup**

Download the last version of the Bullseye Raspberri PI OS and flash it to the SD card.
You can use the [Raspberry Pi imager](https://www.raspberrypi.com/software/) to download and flash the OS.

Activate the SSH, I2S and configure the localisation and WLAN options

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

## Git setup ##
Install git
```bash
sudo apt install git
```
setup identity:
```bash
git config --global user.name "John Doe"
git config --global user.email johndoe@example.com
```
[Generate and add SSH key to your github account](https://docs.github.com/es/authentication/connecting-to-github-with-ssh/generating-a-new-ssh-key-and-adding-it-to-the-ssh-agent)

## Clone the project ##
```bash
git clone git@github.com:<git_user_id>/rpi-electrical-panel.git
```

## Install project dependencies ##

Install the project dependencies in a virtual environement

To install the dependencies manager [poetry](https://python-poetry.org/)

```bash
curl -sSL https://raw.githubusercontent.com/python-poetry/poetry/master/install-poetry.py | python -
```

```bash
sudo apt-get install python3-venv
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

Create logfiles

Log files defined in configuration file located in *server/config/logging-config.yml* must be created before launching the application

```bash
mkdir logs
touch logs/mqtt.log logs/api-rest.log logs/app.log
```

## **Disable Bluethoot and Wifi interfaces**
```bash
sudo nano /boot/config.txt
```

Find the section *[all]* and add the following lines
```bash
dtoverlay=disable-wifi
dtoverlay=disable-bt
```

## **Run the rpi-electrical-panel application**

Set the flask environment variables:

```bash
export FLASK_APP="server/app:create_app()"
export FLASK_ENV=production
```
Run the application

```bash
flask run
```

**You can run the application via VS Code running the `RPI Electrical Panel` configuration**

## **Set the rpi-electrical-panel application as a service**

Copy the service file
```bash
sudo cp service/rpi-electrical-panel.service /etc/systemd/system/
```

Register service
```bash
sudo systemctl daemon-reload
sudo systemctl enable rpi-electrical-panel
sudo systemctl restart rpi-electrical-panel
```

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

* [X] Define logs rotation policy
* [ ] MQTT Messages model as external lib
* [X] MQTT reconnection procedure
* [X] Methods docs
* [X] Relays state -> status
* [X] Errors handle
* [X] Time params to conf
* [ ] Explain MQTT broker and topics in doc (Confluence ?)
* [ ] Explain MQTT messages in doc (Confluence ?)
