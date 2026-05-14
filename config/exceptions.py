from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status
import logging

logger = logging.getLogger(__name__)


def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)

    if response is not None:
        error_data = {
            "success": False,
            "status_code": response.status_code,
            "errors": response.data,
        }
        response.data = error_data
        return response

    logger.exception("Unhandled exception: %s", exc)
    return Response(
        {"success": False, "status_code": 500, "errors": "Internal server error."},
        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )
