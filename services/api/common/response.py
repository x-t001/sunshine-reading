from typing import Any

from rest_framework.response import Response


def success_response(data: Any = None, message: str = "success", code: int = 0, status_code: int = 200) -> Response:
    return Response(
        {
            "code": code,
            "message": message,
            "data": data if data is not None else {},
        },
        status=status_code,
    )


def error_response(data: Any = None, message: str = "error", code: int = 10000, status_code: int = 400) -> Response:
    return Response(
        {
            "code": code,
            "message": message,
            "data": data if data is not None else {},
        },
        status=status_code,
    )
