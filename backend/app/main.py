from fastapi import FastAPI
from app.db.database import test_connection
from app.api.documents import router as documents_router

app = FastAPI()

from app.db.database import test_connection

app.include_router(documents_router)

@app.on_event("startup")
def startup():
    test_connection()


@app.get("/")
def root():
    print("Ask AI is running")
    #return {"message": "Ask AI API is running"}


@app.get("/health")
def health():
    return {"status": "healthy"}





