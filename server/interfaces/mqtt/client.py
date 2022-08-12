import logging
from typing import Callable
import time
from socket import error as socket_error
import paho.mqtt.client as mqtt
from .model import Msg, serialize, deserialize

logger = logging.getLogger(__name__)

# TODO: DOCS

# TODO: validate max connection retries default value
DEFAULT_MAX_CONNECTION_RETRIES = 10
# TODO: validate reconnection timeout
RECONNECTION_TIMEOUT_IN_SEG = 1


class MQTTClient:
    """Service class for MQTT client"""

    def __init__(
        self,
        broker_address: str,
        username: str,
        password: str = None,
        subscriptions: dict = None,
        qos: int = 1,
        max_connection_retries: int = DEFAULT_MAX_CONNECTION_RETRIES,
    ):
        uid = str(time.time_ns())
        self.username = f"{username}_{uid}"
        self.broker_address = broker_address
        self.password = password
        self.subscriptions = subscriptions
        self.qos = qos
        self.max_connection_retries = max_connection_retries
        self._callbacks = {}

        self._client = mqtt.Client(self.username)
        if password:
            self._client.username_pw_set(username=self.username, password=self.password)

        def on_connect(client, userdata, flags, rc, qos=1):
            logger.info("MQTT Client connection established")
            if self.subscriptions is not None:
                for topic, callback in self.subscriptions.items():
                    self.subscribe(topic, callback, qos)
                    logger.info(f"Subscribed to topic: {topic} qos: {qos}")

        def on_disconnect(client, userdata, reasonCode):
            logger.debug("MQTT Client disconnected")
            self.loop_stop()

        def on_subscribe(client, userdata, mid, granted_qos):
            logger.debug("Subscription done garanted_qos: " + str(granted_qos))

        def on_message(client, userdata, message):
            logger.debug(f"Message received on topic {message.topic}")
            # logger.debug(f"   mid : {message.mid}")
            # logger.debug(f"   duplicated : {message.dup}")
            # logger.debug(f"   qos : {message.qos}")
            callback = self._callbacks[message.topic]
            if callback:
                try:
                    msg = deserialize(message.payload)
                    logger.info(f"Message : {str(msg)}")
                    callback(msg)
                except Exception:
                    logger.exception("Message processing failed")
                    raise

        def on_publish(client, userdata, mid):
            logger.debug("Message puback received for message mid: %s", str(mid))

        self._client.on_connect = on_connect
        self._client.on_disconnect = on_disconnect
        self._client.on_subscribe = on_subscribe
        self._client.on_message = on_message
        self._client.on_publish = on_publish

    def connect(self):
        # max_connection_retries is the max number of connection atemps
        # that a client will do before stop before giving up
        try:
            return self._client.connect(self.broker_address)
        except socket_error:
            logger.exception("Connection to broker unsuccessful")
            logger.info("Retrying connection ...")
            time.sleep(RECONNECTION_TIMEOUT_IN_SEG)
            if self.max_connection_retries == 1:
                logger.exception(f"Imposible to connect to broker: {self.broker_address}")
                raise MaxConnectionAttemps(f"Imposible to connect to broker: {self.broker_address}")
            self.max_connection_retries = -1
            return self.connect()

    def disconnect(self):
        logger.info("Disconnect from broker")
        self._client.disconnect()

    def publish(self, topic: str, message: Msg, qos=1):
        logger.debug(f"Publish message on topic {topic}")
        logger.debug(f"Message : {str(message)}")
        if not self._client.is_connected():
            logger.debug("Connection to broker lost, reconnecting ...")
            try:
                self.connect()
                self.loop_start()
                time.sleep(2)
            except socket_error:
                return self.publish(topic, message)
            return self.publish(topic, message)

        message_publish_info = self._client.publish(topic, serialize(message), qos)
        logger.debug("trying to publish message mid: %s", str(message_publish_info.mid))
        return message_publish_info

    def subscribe(self, topic: str, callback: Callable[[Msg], None], qos=1):
        logger.debug(f"Subscribe to topic {topic}")
        self._callbacks[topic] = callback

        return self._client.subscribe(topic, qos)

    def loop_forever(self):
        logger.debug("Run infinite loop")
        self._client.loop_forever()

    def loop_start(self):
        logger.debug("Start loop in dedicated thread")
        return self._client.loop_start()

    def loop_stop(self):
        logger.debug("Stop loop")
        return self._client.loop_stop()


class MaxConnectionAttemps(Exception):
    def __init__(self, *args):
        if args:
            self.message = args[0]
        else:
            self.message = None

    def __str__(self):
        if self.message:
            return "MaxConnectionAttemps, {0}".format(self.message)
        else:
            return "MaxConnectionAttemps has been raised"
