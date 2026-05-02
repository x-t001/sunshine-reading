from rest_framework import status
from rest_framework.exceptions import (
    AuthenticationFailed,
    NotAuthenticated,
    NotFound,
    PermissionDenied,
    ValidationError,
)
from rest_framework.views import exception_handler as drf_exception_handler

from common.response import error_response


def _first_error_message(detail):
    if isinstance(detail, list):
        return str(detail[0]) if detail else "请求参数错误。"
    if isinstance(detail, dict):
        for value in detail.values():
            return _first_error_message(value)
        return "请求参数错误。"
    return str(detail)


def custom_exception_handler(exc, context):
    response = drf_exception_handler(exc, context)
    if response is None:
        return None

    detail = response.data.get("detail", response.data) if isinstance(response.data, dict) else response.data

    if isinstance(exc, ValidationError):
        return error_response(data=response.data, message=_first_error_message(response.data), code=10001, status_code=response.status_code)
    if isinstance(exc, (NotAuthenticated, AuthenticationFailed)):
        return error_response(message=_first_error_message(detail), code=10002, status_code=status.HTTP_401_UNAUTHORIZED)
    if isinstance(exc, PermissionDenied):
        return error_response(message=_first_error_message(detail), code=10003, status_code=status.HTTP_403_FORBIDDEN)
    if isinstance(exc, NotFound):
        return error_response(message=_first_error_message(detail), code=10004, status_code=status.HTTP_404_NOT_FOUND)

    return error_response(message=_first_error_message(detail), code=10000, status_code=response.status_code)
