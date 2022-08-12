# import smbus
import logging
from typing import Iterable
from flask import Flask
from server.interfaces.mqtt import mqtt_client_interface
from datetime import datetime
from timeloop import Timeloop
from server.interfaces.mqtt import SingleRelayStatus, RelaysStatus
from datetime import timedelta
import time

# TODO Status -> state

relays_status_timeloop = Timeloop()

logger = logging.getLogger(__name__)

# bus = smbus.SMBus(1)


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

            # Set the I2C address
            self.last_received_command_timestamp = datetime.now()
            # TODO: set in config
            self.serial_address = 0x20

            # Connect to MQTT broker
            self.init_mqtt_service()

    def generate_serial_command(self, new_relay_statuses: Iterable[SingleRelayStatus]):
        """Generate serial command to send to control the relays"""

        relays_current_state_raw, relays_current_states = self.get_relays_current_states()
        relays_with_new_state = []

        # Retreive the relays that change of state
        for new_relay_status in new_relay_statuses:
            if new_relay_status.relay_number in relays_current_states:
                if new_relay_status.status != relays_current_states[new_relay_status.relay_number]:
                    relays_with_new_state.append(new_relay_status.relay_number)
        logger.info(f"relays_with_new_states: {relays_with_new_state}")
        # generate command
        new_state_raw_command = bin(relays_current_state_raw)[2:]
        for i in relays_with_new_state:
            new_status = "0" if relays_current_states[i] else "1"
            new_state_raw_command = (
                new_state_raw_command[: i + 2] + new_status + new_state_raw_command[i + 3 :]
            )
        relays_new_status_command = int(new_state_raw_command, 2)

        logger.info(f"Generated command: {relays_new_status_command}")
        return relays_new_status_command

    def get_relays_current_states(self):
        """retrieve relays current status and format"""
        relays_states = {}

        # ONLY FOR LOCAL TEST
        # current_state_raw = 0xCC  # 0b11001100
        current_state_raw = 0xCC  # 0b00000000

        # current_state_raw = ~bus.read_byte(self.serial_address) & 0xFF
        current_state = "{0:08b}".format(current_state_raw)[2:]

        for i, state in enumerate(current_state):
            relay_status = True if state == "1" else False
            relays_states[i] = relay_status

        # logger.debug(f"Retrieved current state : {current_state}")
        # logger.info(f"Relays current states: {relays_states}")
        return current_state_raw, relays_states

    def get_relays_current_states_instance(self):
        """retrieve relays current status as a RelaysStatus instance"""

        current_state_raw, relays_current_states = self.get_relays_current_states()
        relay_statuses = []
        for relay_number, relay_status in relays_current_states.items():
            relay_statuses.append(SingleRelayStatus(relay_number=relay_number, status=relay_status))
        relays_current_states = RelaysStatus(relay_statuses=relay_statuses, command=False)

        return current_state_raw, relays_current_states

    def get_single_relay_state_instance(self, relay_number: int):
        """get single relay status as a SingleRelayStatus instance"""

        if relay_number not in range(0, 6):
            # TODO raise exception
            return None

        _, relays_statuses = self.get_relays_current_states_instance()

        for relay_status in relays_statuses.relay_statuses:
            if relay_status.relay_number == relay_number:
                return relay_status

        # TODO raise exception if relay not found
        return None

    def send_relays_command(self, serial_command: str):
        """send relays control serial command"""
        logger.info(f"Sending serial command: {serial_command}")

        raw_command = ~serial_command & 0xFF
        logger.debug(f"Raw command: {raw_command}")

        # Writte serial command
        # bus.write_byte(self.serial_address, raw_command)

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
        # TODO: time in conf
        @relays_status_timeloop.job(interval=timedelta(seconds=5))
        def send_relays_status():
            # retrieve relays status
            if self.mqtt_client.connected:
                current_state_raw, relays_current_states = self.get_relays_current_states_instance()
                logger.info(f"Publish current relays status: {bin(current_state_raw)}")
                self.mqtt_client.publish(
                    topic=self.mqtt_relays_status_topic, message=relays_current_states
                )
            else:
                logger.info(f"MQTT Client disconnected, relays status not sent")

        relays_status_timeloop.start(block=False)


relays_manager_service: RelaysManager = RelaysManager()
""" Relays manager service singleton"""
