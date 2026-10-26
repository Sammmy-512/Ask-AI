import app.models
from fastapi import FastAPI
from app.db.database import test_connection
from app.api.documents import router as documents_router
from app.api.query import router as query_router
from app.core.logging_config import configure_logging
from app.core.request_logging import RequestLoggingMiddleware
from contextlib import asynccontextmanager
import sys


if "pytest" not in sys.modules:
    configure_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    test_connection()
    yield


app = FastAPI(lifespan=lifespan)


app.add_middleware(RequestLoggingMiddleware)
app.include_router(documents_router)
app.include_router(query_router)




@app.get("/")
def root():
    print("Ask AI is running")
    #return {"message": "Ask AI API is running"}


@app.get("/health")
def health():
    return {"status": "healthy"}





