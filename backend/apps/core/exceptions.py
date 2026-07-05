import logging

from rest_framework.views import exception_handler

logger = logging.getLogger("voidlab.api")


def voidlab_exception_handler(exc, context):
    """Wrap DRF's default handler so every error response has a predictable
    shape the frontend can rely on: {"error": {"code": ..., "detail": ...}}.
    """
    response = exception_handler(exc, context)

    if response is not None:
        request = context.get("request")
        request_id = getattr(request, "request_id", None)
        response.data = {
            "error": {
                "code": response.status_code,
                "detail": response.data,
                "request_id": request_id,
            }
        }
        logger.warning(
            "API error %s on %s (request_id=%s): %s",
            response.status_code,
            getattr(request, "path", "?"),
            request_id,
            response.data,
        )

    return response
