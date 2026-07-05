import uuid


class RequestIDMiddleware:
    """Attach a unique X-Request-ID to every request/response pair.

    Makes it far easier to correlate a single user action across the
    Django logs, the WebSocket terminal session, and the vulnerable-app
    containers when debugging a lab end to end.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        response = self.get_response(request)
        response["X-Request-ID"] = request.request_id
        return response
