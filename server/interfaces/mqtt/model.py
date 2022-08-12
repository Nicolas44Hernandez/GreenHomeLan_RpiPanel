"""
MQTT messages model
"""
# TODO: DOCS

from datetime import datetime
from typing import Iterable, TypeVar
from enum import Enum
import bson
import dateutil.parser

Msg = TypeVar("Msg")


def serialize(msg: Msg) -> bytes:
    return bson.dumps(msg.to_json())


def deserialize(payload: bytes) -> Msg:
    return RelaysStatus.from_json(bson.loads(payload))


class SingleRelayStatus:
    def __init__(self, relay_number: int, status: bool):
        self.relay_number = relay_number
        self.status = status

    def __str__(self):
        return "{}".format({"relay_number": self.relay_number, "status": self.status})

    def to_json(self):
        return {"relay_number": self.relay_number, "status": self.status}

    def from_json(dictionary: dict):
        return SingleRelayStatus(
            relay_number=dictionary["relay_number"],
            status=dictionary["status"],
        )


class RelaysStatus:
    def __init__(
        self, relay_statuses: Iterable[SingleRelayStatus], command: bool, timestamp: datetime = None
    ):
        self.relay_statuses = relay_statuses
        self.command = command
        self.timestamp = datetime.now() if timestamp is None else timestamp

    def __str__(self):
        return "{}".format(
            {
                "relay_statuses": [str(relay_status) for relay_status in self.relay_statuses],
                "timestamp": self.timestamp.isoformat(),
                "command": self.command,
            },
        )

    def to_json(self):
        return {
            "relay_statuses": [relay_status.to_json() for relay_status in self.relay_statuses],
            "timestamp": self.timestamp.isoformat(),
            "command": self.command,
        }

    def from_json(dictionary: dict):
        return RelaysStatus(
            relay_statuses=[
                SingleRelayStatus.from_json(single_relay_dict)
                for single_relay_dict in dictionary["relay_statuses"]
            ],
            command=dictionary["command"],
            timestamp=dateutil.parser.isoparse(dictionary["timestamp"]),
        )
