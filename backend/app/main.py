from fastapi import FastAPI
from app.db.database import test_connection

app = FastAPI()

from app.db.database import test_connection

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





