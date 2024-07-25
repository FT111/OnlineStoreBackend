from pydantic import BaseModel, Field, EmailStr, model_validator, HttpUrl, field_validator
from typing import List, Optional, Union, Dict, Any, Tuple, Set
from typing_extensions import Annotated
from fastapi import FastAPI, Response, Request, APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from asyncio import sleep

router = APIRouter(prefix="/")
