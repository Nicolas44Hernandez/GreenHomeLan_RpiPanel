""" RPI electtical pannel errors """

from enum import Enum


class ErrorCode(Enum):
    """Enumerate which gather all data about possible errors"""

    # Please enrich this enumeration in order to handle other kind of errors
    UNEXPECTED_ERROR = (0, 500, "Unexpected error occurs")
    INVALID_RELAY_NUMBER = (1, 400, "Invalid relay number")
    RELAYS_NUMBER_DONT_MATCH = (2, 400, "Relay numbers dont match")

    # pylint: disable=unused-argument
    def __new__(cls, *args, **kwds):
        """Custom new in order to initialize properties"""
        obj = object.__new__(cls)
        obj._value_ = args[0]
        obj._http_code_ = args[1]
        obj._message_ = args[2]
        return obj

    @property
    def http_code(self):
        """The http code corresponding to the error"""
        return self._http_code_

    @property
    def message(self):
        """The message corresponding to the error"""
        return self._message_
