from rest_framework.decorators import api_view

from common.api_response import success_response


@api_view(["GET"])
def health_check(request):
    return success_response(
        data={
            "status": "ok",
            "service": "sunshine-reading-api",
        }
    )
