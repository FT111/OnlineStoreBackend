import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app import instances
from app.middleware import GetUserMiddleware, HandleAnalyticsMiddleware
from app.routes.analytics import router as analyticsRouter
from app.routes.auth import router as authRouter
from app.routes.categories import router as categoriesRouter
from app.routes.listings import router as listingsRouter
from app.routes.transactions import router as transactionsRouter
from app.routes.users import router as usersRouter

app = FastAPI()

app.include_router(listingsRouter)
app.include_router(categoriesRouter)
app.include_router(authRouter)
app.include_router(usersRouter)
app.include_router(transactionsRouter)
app.include_router(analyticsRouter)

app.mount("/static", StaticFiles(directory="app/static"), name="static")

app.state.limiter = instances.rateLimiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
	CORSMiddleware,
	allow_origins=["http://localhost:4173", "http://localhost:5173", "http://172.16.104.213:4173", "http://localhost:5174", "http://localhost:3000", "http://0.0.0.0:3000"],
	allow_credentials=True,
	allow_methods=["GET", "POST", "PUT", "DELETE"],
	allow_headers=['*'],
)

app.add_middleware(
	HandleAnalyticsMiddleware
)

app.add_middleware(
	GetUserMiddleware
)
if __name__ == "__main__":
	uvicorn.run(app, host="0.0.0.0", port=8000)
