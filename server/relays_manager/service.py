import smbus
import logging
from typing import Iterable
from flask import Flask
from server.interfaces.mqtt import mqtt_client_interface
from datetime import datetime
from timeloop import Timeloop
from server.interfaces.mqtt import SingleRelayStatus, RelaysStatus
from datetime import timedelta
from server.common import RpiElectricalPanelException, ErrorCode


relays_status_timeloop = Timeloop()

logger = logging.getLogger(__name__)

bus = smbus.SMBus(1)


class RelaysManager:
    """Manager for relays control"""

    mqtt_broker_address: str
    mqtt_username: str
    mqtt_password: str
    mqtt_command_relays_topic: str
    mqtt_relays_status_topic: str
    mqtt_qos: int
    mqtt_reconnection_timeout_in_secs: int
    mqtt_publish_timeout_in_secs: int
    last_received_command_timestamp: datetime

    def __init__(self, app: Flask = None) -> None:
        if app is not None:
            self.init_app(app)

    def init_app(self, app: Flask) -> None:
        """Initialize RelaysManager"""
        if app is not None:
            logger.debug("initializing the RelaysManager")
            # Initialize configuration
            self.mqtt_broker_address = app.config["MQTT_BROKER_ADDRESS"]
            self.mqtt_username = app.config["MQTT_USERNAME"]
            self.mqtt_password = app.config["MQTT_PASSWORD"]
            self.mqtt_command_relays_topic = app.config["MQTT_COMMAND_RELAYS_TOPIC"]
            self.mqtt_relays_status_topic = app.config["MQTT_RELAYS_STATUS_TOPIC"]
            self.mqtt_qos = app.config["MQTT_QOS"]
            self.mqtt_reconnection_timeout_in_secs = app.config["MQTT_RECONNECTION_TIMEOUT_IN_SEG"]
            self.mqtt_publish_timeout_in_secs = app.config["MQTT_MSG_PUBLISH_TIMEOUT_IN_SECS"]
            self.serial_address = app.config["RELAYS_SERIAL_ADDRESS"]
            self.relays_status_notification_period_in_secs = app.config[
                "RELAYS_STATUS_NOTIFICATION_PERIOD_IN_SECS"
            ]

            # Set the I2C address
            self.last_received_command_timestamp = datetime.now()

            # Connect to MQTT broker
            self.init_mqtt_service()

            # Init relays status
            self.init_relays_status()

    def generate_serial_command(self, new_relay_statuses: Iterable[SingleRelayStatus]):
        """Generate serial command to send to control the relays"""

        relays_current_status_raw, relays_current_status = self.get_relays_current_status()
        relays_with_new_status = []

        # Retreive the relays that change of status
        for new_relay_status in new_relay_statuses:
            if new_relay_status.relay_number in relays_current_status:
                if new_relay_status.status != relays_current_status[new_relay_status.relay_number]:
                    relays_with_new_status.append(new_relay_status.relay_number)
        logger.info(f"relays_with_new_status: {relays_with_new_status}")

        # generate command
        new_status_raw_command = bin(relays_current_status_raw)[2:]
        for i in relays_with_new_status:
            new_status = "0" if relays_current_status[i] else "1"
            new_status_raw_command = (
                new_status_raw_command[: i + 2] + new_status + new_status_raw_command[i + 3 :]
            )
        relays_new_status_command = int(new_status_raw_command, 2)

        logger.info(f"Generated command: {relays_new_status_command}")
        return relays_new_status_command

    def get_relays_current_status(self):
        """retrieve relays current status and format"""
        relays_status = {}

        # ONLY FOR LOCAL TEST
        # current_status_raw = 0xCC  # 0b11001100
        # current_status_raw = 0xCC  # 0b00000000

        current_status_raw = ~bus.read_byte(self.serial_address) & 0xFF
        current_status = "{0:08b}".format(current_status_raw)[2:]

        for i, status in enumerate(current_status):
            relay_status = True if status == "1" else False
            relays_status[i] = relay_status

        logger.debug(f"Relays current status: {relays_status}")
        return current_status_raw, relays_status

    def get_relays_current_status_instance(self):
        """retrieve relays current status as a RelaysStatus instance"""

        current_status_raw, relays_current_status = self.get_relays_current_status()
        relay_statuses = []
        for relay_number, relay_status in relays_current_status.items():
            relay_statuses.append(SingleRelayStatus(relay_number=relay_number, status=relay_status))
        relays_current_status = RelaysStatus(relay_statuses=relay_statuses, command=False)

        return current_status_raw, relays_current_status

    def get_single_relay_status_instance(self, relay_number: int):
        """get single relay status as a SingleRelayStatus instance"""

        if relay_number not in range(0, 6):
            raise RpiElectricalPanelException(ErrorCode.INVALID_RELAY_NUMBER)

        _, relays_statuses = self.get_relays_current_status_instance()

        for relay_status in relays_statuses.relay_statuses:
            if relay_status.relay_number == relay_number:
                return relay_status
        return None

    def send_relays_command(self, serial_command: str):
        """send relays control serial command"""
        logger.info(f"Sending serial command: {serial_command}")

        raw_command = ~serial_command & 0xFF
        logger.debug(f"Raw command: {raw_command}")

        # Writte serial command
        bus.write_byte(self.serial_address, raw_command)

    def set_relays_statuses(self, relays_status: RelaysStatus):
        """Set relays statuses, used as callback for messages received in command relays topic"""
        logger.debug(f"Relays command received : {relays_status}")
        if relays_status.timestamp < self.last_received_command_timestamp:
            logger.info(f"Command rejected, the timestamp is too old")
            return None

        relays_new_status_serial_command = self.generate_serial_command(
            relays_status.relay_statuses
        )
        # Send relays serial command
        self.send_relays_command(relays_new_status_serial_command)

        # notify new relays status
        self.notify_relays_status()

    def notify_relays_status(self):
        """Pubish MQTT message to notify relays status"""
        # retrieve relays status
        if self.mqtt_client.connected:
            current_status_raw, relays_current_status = self.get_relays_current_status_instance()
            logger.info(f"Publish current relays status: {bin(current_status_raw)}")
            self.mqtt_client.publish(
                topic=self.mqtt_relays_status_topic, message=relays_current_status
            )
        else:
            logger.info(f"MQTT Client disconnected, relays status not sent")

    def init_relays_status(self):
        """Set relays status to OFF"""

        # Initial relays status
        relays_statuses = [
            SingleRelayStatus(relay_number=0, status=False),
            SingleRelayStatus(relay_number=1, status=False),
            SingleRelayStatus(relay_number=2, status=False),
            SingleRelayStatus(relay_number=3, status=False),
            SingleRelayStatus(relay_number=4, status=False),
            SingleRelayStatus(relay_number=5, status=False),
        ]
        initial_relays_status = RelaysStatus(relay_statuses=relays_statuses, command=True)

        # Set initial status
        self.set_relays_statuses(relays_status=initial_relays_status)

    def init_mqtt_service(self):
        """Connect to MQTT broker"""

        self.mqtt_client = mqtt_client_interface(
            broker_address=self.mqtt_broker_address,
            username=self.mqtt_username,
            password=self.mqtt_password,
            subscriptions={self.mqtt_command_relays_topic: self.set_relays_statuses},
            reconnection_timeout_in_secs=self.mqtt_reconnection_timeout_in_secs,
            publish_timeout_in_secs=self.mqtt_publish_timeout_in_secs,
        )
        self.mqtt_client.connect()
        self.mqtt_client.loop_start()

        # Start relays status notification service
        @relays_status_timeloop.job(
            interval=timedelta(seconds=self.relays_status_notification_period_in_secs)
        )
        def send_relays_status():
            self.notify_relays_status()

        relays_status_timeloop.start(block=False)


relays_manager_service: RelaysManager = RelaysManager()
""" Relays manager service singleton"""
