from pydantic import BaseModel, Field, EmailStr, model_validator, HttpUrl, field_validator
from typing import List, Optional, Union, Dict, Any, Tuple, Set
from typing_extensions import Annotated
from fastapi import FastAPI, Response, Request, APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from asyncio import sleep
from starlette.middleware.base import BaseHTTPMiddleware

from app.functions.auth import validateTokenUser


class GetUserMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):

        authHeader = request.headers.get('authorization')
        JWT = authHeader.split(' ')[1] if authHeader else None

        if JWT:
            user = validateTokenUser(JWT)
            if user:
                request.state.user = user
            else:
                request.state.user = None
        else:
            request.state.user = None

        print(request.state.user)
        print(request.headers)
        response = await call_next(request)
        return response

