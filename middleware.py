from fastapi import Request
from fastapi.responses import RedirectResponse
from nicegui import Client, app
from starlette.middleware.base import BaseHTTPMiddleware

unrestricted_page_routes = {"/login"}


class AuthMiddleware(BaseHTTPMiddleware):
    """This middleware restricts access to all NiceGUI pages.

    It redirects the user to the login page if they are not authenticated.
    """

    async def dispatch(self, request: Request, call_next):
        if not app.storage.user.get("authenticated", False):
            if request.url.path in Client.page_routes.values() and request.url.path not in unrestricted_page_routes:
                app.storage.user["referrer_path"] = request.url.path  # remember where the user wanted to go
                return RedirectResponse("/login")
        return await call_next(request)
