""" REST controller for relays management ressource """
import logging
from datetime import datetime
from flask.views import MethodView
from flask_smorest import Blueprint

from server.relays_manager import relays_manager_service
from .rest_model import SingleRelayStatusSchema, RelaysStatusResponseSchema, RelaysStatusQuerySchema
from server.interfaces.mqtt.model import SingleRelayStatus, RelaysStatus
from server.common import RpiElectricalPanelException, ErrorCode


RELAYS = ["relay_0", "relay_1", "relay_2", "relay_3", "relay_4", "relay_5"]

logger = logging.getLogger(__name__)

bp = Blueprint("relays", __name__, url_prefix="/relays")
""" The api blueprint. Should be registered in app main api object """


@bp.route("/")
class RelaysStatusApi(MethodView):
    """API to retrieve or set wifi general status"""

    @bp.doc(
        responses={400: "BAD_REQUEST", 404: "NOT_FOUND"},
    )
    @bp.response(status_code=200, schema=RelaysStatusResponseSchema)
    def get(self):
        """Get relays status"""

        logger.info(f"GET relays/")

        # Call relays manager services to get relays status
        _, relays_status = relays_manager_service.get_relays_current_status_instance()

        return relays_status

    @bp.doc(responses={400: "BAD_REQUEST"})
    @bp.arguments(RelaysStatusQuerySchema, location="query")
    @bp.response(status_code=200, schema=RelaysStatusResponseSchema)
    def post(self, args: RelaysStatusQuerySchema):
        """Set relays status"""

        logger.info(f"POST relays/ {args}")

        # Build RelayStatus instance
        statuses_from_query = []
        for relay in RELAYS:
            if relay in args:
                statuses_from_query.append(
                    SingleRelayStatus(relay_number=int(relay.split("_")[1]), status=args[relay]),
                )

        relays_statuses = RelaysStatus(
            relay_statuses=statuses_from_query, command=True, timestamp=datetime.now()
        )

        # Call relays_manager_service to set relays statuses
        relays_manager_service.set_relays_statuses(relays_status=relays_statuses, notify=True)
        return relays_statuses


@bp.route("/single/<relay>")
class WifiBandsStatusApi(MethodView):
    """API to retrieve single relay status"""

    @bp.doc(
        responses={400: "BAD_REQUEST", 404: "NOT_FOUND"},
    )
    @bp.response(status_code=200, schema=SingleRelayStatusSchema)
    def get(self, relay: str):
        """Get single relay status"""

        logger.info(f"GET relays/sinle/{relay}")

        # Call relays_manager_service to get relay status
        return relays_manager_service.get_single_relay_status_instance(int(relay))

    @bp.doc(responses={400: "BAD_REQUEST"})
    @bp.arguments(SingleRelayStatusSchema, location="query")
    @bp.response(status_code=200, schema=SingleRelayStatusSchema)
    def post(self, args: SingleRelayStatusSchema, relay: str):
        """Set single relays status"""

        logger.info(f"POST relays/sinle/{relay} {args}")

        relay_number = int(relay)
        # Sanity check
        if relay_number != args["relay_number"]:
            raise RpiElectricalPanelException(ErrorCode.RELAYS_NUMBER_DONT_MATCH)

        # Sanity check
        if relay_number not in range(0, 6):
            raise RpiElectricalPanelException(ErrorCode.INVALID_RELAY_NUMBER)

        single_relay_status = SingleRelayStatus(relay_number=relay_number, status=args["status"])

        # Call relays_manager_service to set relays statuses
        relays_status = RelaysStatus(
            relay_statuses=[single_relay_status],
            command=True,
            timestamp=datetime.now(),
        )
        relays_manager_service.set_relays_statuses(relays_status=relays_status, notify=True)

        return single_relay_status
