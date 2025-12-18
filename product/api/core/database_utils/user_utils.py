from asyncpg import Connection, Pool

__all__ = ["UsersWorker"]

class UsersWorker:
    def __init__(self, db_pool: Pool) -> None:
        self._db_pool: Pool = db_pool

    async def add_user(self, user_id: str) -> None:
        sql_template = f"""
            INSERT INTO users (user_id) 
            VALUES ($1) 
            ON CONFLICT (user_id) DO NOTHING;
        """
        async with self._db_pool.acquire() as conn:
            conn: Connection
            await conn.fetchval(sql_template, user_id)

    async def vote(self, user_id: str, place_id: int, score: float) -> bool:
        sql_template = """
            INSERT INTO votes (user_id, place_id, score)
            VALUES ($1, $2, $3)
            ON CONFLICT ON CONSTRAINT unique_user_place 
            DO NOTHING
            RETURNING vote_id
        """
        async with self._db_pool.acquire() as conn:
            conn: Connection
            result = await conn.fetchval(sql_template, user_id, place_id, score)
            return result is not None
        return False
