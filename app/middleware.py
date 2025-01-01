from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

from app.functions.auth import validateToken


class GetUserMiddleware(BaseHTTPMiddleware):
    """
    Checks for a JWT token in the request header, validates it, and adds the user to the request state
    """
    async def dispatch(self, request: Request, call_next):

        # Get the bearer header from the request
        authHeader = request.headers.get('Authorization')
        print('authHeader', authHeader)

        # Get the JWT token from the header
        JWT = authHeader.split(' ')[1] if authHeader else None

        # Validates the token if it exists, returns the user if valid
        if JWT:
            user = validateToken(JWT)
            if user:
                request.state.user = user
            else:
                request.state.user = None
        else:
            request.state.user = None

        print(request.cookies)

        # Continue the request
        response = await call_next(request)

        # Return the response
        return response

