from fastapi import FastAPI, Response, Request
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import json, uvicorn, random
from asyncio import sleep

from app.models.response import ResponseSchema
from app.routes.listings import router as listingsRouter

app = FastAPI()

app.include_router(listingsRouter)

# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"],
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )


# @app.middleware("http")
# async def responseScheme(request: Request, call_next):
#     response = await call_next(request)
#
#     # if response.body:
#     #     request.body = await ResponseSchema(data=response.body)
#     print(response)
#
#     return response

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
