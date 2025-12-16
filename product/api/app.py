from fastapi import FastAPI
from asyncpg import connect, Connection
import os

app: FastAPI = FastAPI()

DATABASE_URL: str = os.getenv("DATABASE_URL")

async def get_db_connection() -> Connection:
    return await connect(DATABASE_URL)

@app.get("/ping")
async def ping() -> dict[str, str]:
    return {"service": "api"}

@app.get("/check-db")
async def check_db() -> dict[str, str]:
    try:
        conn = await get_db_connection()
        result = await conn.fetch("SELECT COUNT(*) as count FROM test_table")
        await conn.close()
        return {"database": "connected", "records_count": result[0]["count"]}
    except Exception as e:
        return {"database": "error", "error": str(e)}