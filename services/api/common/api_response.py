from typing import Any, Dict, Optional

from rest_framework.response import Response


def success_response(data: Optional[Dict[str, Any]] = None, message: str = "success", code: int = 0, status_code: int = 200) -> Response:
    return Response(
        {
            "code": code,
            "message": message,
            "data": data or {},
        },
        status=status_code,
    )


def error_response(message: str = "error", code: int = 10000, data: Optional[Dict[str, Any]] = None, status_code: int = 400) -> Response:
    return Response(
        {
            "code": code,
            "message": message,
            "data": data or {},
        },
        status=status_code,
    )
