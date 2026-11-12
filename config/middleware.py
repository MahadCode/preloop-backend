class CsrfResponseHeaderMiddleware:
    """Copy the CSRF cookie onto a response header the browser is allowed to read.

    The frontend and API are different sites in production, so page JavaScript
    cannot read the API host's csrftoken cookie. Django still expects that
    token in X-CSRFToken, and it rotates the cookie after login.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        token = request.META.get("CSRF_COOKIE")
        if token:
            response["X-CSRFToken"] = token
        return response
