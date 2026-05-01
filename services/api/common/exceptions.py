"""
Project-level DRF exception handler placeholder.

Current behavior:
- delegates to DRF default handler
- keeps unified response extension point in one place

Next step:
- normalize non-field errors and validation details to project code format
"""

from rest_framework.views import exception_handler as drf_exception_handler


def custom_exception_handler(exc, context):
    response = drf_exception_handler(exc, context)
    return response
