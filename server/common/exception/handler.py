""" Exception handler module for REST API """

from flask import jsonify
from .model import RpiElectricalPanelException


def handle_rpi_electrical_panel_exception(ex: RpiElectricalPanelException):
    """Customize returned body"""

    # Create error response
    response = {
        "code": ex.http_code,
        "status": ex.message,
        "ExceptionCode": ex.code,
    }
    return jsonify(response), ex.http_code
