""" App initialization module."""

import logging
from logging.config import dictConfig
from os import path
import yaml
from flask import Flask
from .relays_manager import relays_manager_service
from .extension import api
from .rest_api.relays_manager import bp as relays_manager_bp


logger = logging.getLogger(__name__)


def create_app(
    config_dir: str = path.join(path.dirname(path.abspath(__file__)), "config"),
):
    """Create the Flask app"""

    # Create app Flask
    app = Flask("Server Box")

    # Get configuration files
    app_config = path.join(config_dir, "rpi-electrical-panel-config.yml")
    logging_config = path.join(config_dir, "logging-config.yml")

    # Load logging configuration and configure flask application logger
    with open(logging_config) as stream:
        dictConfig(yaml.full_load(stream))

    logger.info("App config file: %s", app_config)

    # Load configuration
    app.config.from_file(app_config, load=yaml.full_load)

    # Register extensions
    register_extensions(app)
    # Register blueprints for REST API
    register_blueprints(app)

    logger.info("App ready!!")

    return app


def register_extensions(app):
    """Initialize all extensions"""

    # Initialize REST APIs.
    #
    # The spec_kwargs dict is used to generate the OpenAPI document that describes our APIs.
    # The securitySchemes field defines the security scheme used to protect our APIs.
    #   - BasicAuth  allows to authenticate a user with a login and a password.
    #   - BearerAuth allows to authenticate a user using a token (the /login API allows to a user
    #     to retrieve a valid token).

    api.init_app(
        app,
        spec_kwargs={
            "info": {"description": "`RPI Relays` OpenAPI 3.0 specification."},
            "components": {
                "securitySchemes": {
                    "basicAuth": {"type": "http", "scheme": "basic"},
                    "tokenAuth": {"type": "http", "scheme": "bearer"},
                },
            },
        },
    )

    # Wifi bands manager extension
    relays_manager_service.init_app(app=app)


def register_blueprints(app: Flask):
    """Store App APIs blueprints."""
    # Register error handler
    # TODO: error handler
    # app.register_error_handler(ServerBoxException, handle_server_box_exception)
    # Register REST blueprints
    api.register_blueprint(relays_manager_bp)
