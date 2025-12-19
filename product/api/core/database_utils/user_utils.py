from typing import Any
from asyncpg import Connection, Pool, Record

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
            WITH inserted_vote AS (
                INSERT INTO votes (user_id, place_id, score)
                VALUES ($1, $2, $3)
                ON CONFLICT ON CONSTRAINT unique_user_place 
                DO NOTHING
                RETURNING vote_id, user_id
            )
            UPDATE users
            SET unprocessed_votes = unprocessed_votes + 1,
                total_votes = total_votes + 1
            WHERE user_id = (SELECT user_id FROM inserted_vote)
            RETURNING (SELECT vote_id FROM inserted_vote);
        """
        async with self._db_pool.acquire() as conn:
            conn: Connection
            result = await conn.fetchval(sql_template, user_id, place_id, score)
            return result is not None
        return False
    
    async def get_n_votes(self, user_id: str) -> tuple[int, int]:
        sql_template = """
            SELECT unprocessed_votes, total_votes 
            FROM users 
            WHERE user_id = $1;
        """
        async with self._db_pool.acquire() as conn:
            conn: Connection
            result = await conn.fetchrow(sql_template, user_id)
            
            if result:
                return result["unprocessed_votes"], result["total_votes"]
            return 0, 0
        
    async def clear_unprocessed_votes(self, user_id: str) -> None:
        sql_template = """
            UPDATE users 
            SET unprocessed_votes = 0 
            WHERE user_id = $1;
        """
        async with self._db_pool.acquire() as conn:
            conn: Connection
            await conn.execute(sql_template, user_id)

    async def get_voted_place_ids(self, user_id: str) -> list[int]:
        sql_template = """
            SELECT place_id 
            FROM votes 
            WHERE user_id = $1 
            ORDER BY vote_id;
        """
        async with self._db_pool.acquire() as conn:
            conn: Connection
            rows = await conn.fetch(sql_template, user_id)
            return [row["place_id"] for row in rows]
        
    async def get_voted_places(self, user_id: str) -> list[dict[str, Any]]:
        sql_template = """
            SELECT 
                v.vote_id,
                v.user_id,
                v.place_id,
                v.score,
                p.*
            FROM votes v
            JOIN places p ON v.place_id = p.place_id
            WHERE v.user_id = $1
            ORDER BY v.vote_id;
        """
        async with self._db_pool.acquire() as conn:
            conn: Connection
            rows: list[Record] = await conn.fetch(sql_template, user_id)
            votes_list: list[dict[str, Any]] = []
            for row in rows:
                place_dict = {
                    "score": row["score"]
                }
                place_dict: dict[str, Any] = {}
                for key in row.keys():
                    if key not in ["vote_id", "user_id", "place_id", "score", "total_votes", "is_indexed"]:
                        place_dict[key] = row[key]
                place_dict["place"] = place_dict
                votes_list.append(place_dict)
            return votes_list
        
    async def set_virtual_scores(self, user_id: str, places: list[int], scores: list[float]) -> None:
        if len(places) != len(scores):
            raise ValueError("Length of places and scores must be equal")
        
        if not places:
            return
        
        sql_template = """
            INSERT INTO virtual_scores (user_id, place_id, score)
            SELECT $1, unnest($2::bigint[]), unnest($3::float[])
            ON CONFLICT ON CONSTRAINT unique_user_place_virtuals
            DO UPDATE SET score = EXCLUDED.score;
        """
        async with self._db_pool.acquire() as conn:
            conn: Connection
            await conn.execute(sql_template, user_id, places, scores)

    async def best_predicts(self, 
                            user_id: str, 
                            n_places: int, 
                            disallowed_places: list[int], 
                            allowed_types: list[str], 
                            allowed_towns: list[str]
                           ) -> list[int]:
        sql_template = """
            SELECT vs.place_id
            FROM virtual_scores vs
            INNER JOIN places p ON vs.place_id = p.place_id
            WHERE vs.user_id = $1
              AND vs.place_id != ALL($2::bigint[])
              AND (CARDINALITY($3::text[]) = 0 OR p.type = ANY($3::text[]))
              AND (CARDINALITY($4::text[]) = 0 OR p.town = ANY($4::text[]))
            ORDER BY vs.score DESC, vs.place_id
            LIMIT $5;
        """
        async with self._db_pool.acquire() as conn:
            conn: Connection
            rows = await conn.fetch(
                sql_template, 
                user_id, 
                disallowed_places, 
                allowed_types, 
                allowed_towns, 
                n_places
            )
            return [row["place_id"] for row in rows]
        return []