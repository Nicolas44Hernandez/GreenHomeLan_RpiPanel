import os, sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from server.interfaces.mqtt import mqtt_client_interface
import time
from datetime import datetime

HOST = "192.168.1.16"
CLIENT_NAME = "subscriber_test"
CLIENT_PASSWORD = "lamp"
TOPIC = "status/relays"


def callback_on_receive(message: str):
    print(f"Message received on topic  {TOPIC} {datetime.now()}")
    print(f"{message}")


mqtt_client = mqtt_client_interface(
    broker_address=HOST,
    username=CLIENT_NAME,
    password=CLIENT_PASSWORD,
    subscriptions={TOPIC: callback_on_receive},
)
mqtt_client.connect()
time.sleep(1)

mqtt_client.loop_start()


try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:  # Trap a CTRL+C keyboard interrupt
    mqtt_client.disconnect()
