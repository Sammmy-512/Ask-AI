from fastapi import FastAPI

app = FastAPI()


@app.get("/")
def root():
    print("Ask AI is running")
    return {"message": "Ask AI API is running"}


@app.get("/health")
def health():
    return {"status": "healthy"}





