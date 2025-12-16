from fastapi import FastAPI

app: FastAPI = FastAPI()

@app.get("/ping")
async def ping() -> dict[str, str]:
    return {"service": "llm"}