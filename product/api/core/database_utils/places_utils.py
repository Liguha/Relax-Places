from typing import ClassVar, Any
from asyncpg import Connection, Pool

__all__ = ["PlacesWorker"]

class PlacesWorker:
    FEATURES: ClassVar[list[str]] = [
        "natural_scenery",
        "cultural_richness",
        "adventure_level",
        "family_friendliness",
        "beach_quality",
        "mountain_terrain",
        "urban_vibrancy",
        "food_variety",
        "accommodation_quality",
        "transportation_accessibility",
        "cost_level",
        "safety",
        "relaxation_level",
        "nightlife_intensity",
        "historical_significance"
    ]
        
    def __init__(self, db_pool: Pool, required_votes: int = 3) -> None:
        self._db_pool: Pool = db_pool
        self._min_votes: int = required_votes

    async def upsert_place(self, place_id: int, name: str, description: str, town: str, place_type: str, vote_values: dict[str, str | float]) -> None:
        async with self._db_pool.acquire() as conn:
            conn: Connection
            set_parts = [
                "name = EXCLUDED.name",
                "description = EXCLUDED.description"
                "town = EXCLUDED.town",
                "type = EXCLUDED.type",
                "total_votes = places.total_votes + 1"
            ]
            for field in self.FEATURES:
                new_vote = vote_values.get(field, 0.0)
                set_parts.append(
                    f"{field} = CASE "
                    f"WHEN places.total_votes > 0 "
                    f"THEN (places.{field} * places.total_votes + {new_vote}) / (places.total_votes + 1) "
                    f"ELSE {new_vote} "
                    f"END"
                )
            set_parts.append(
                f"is_indexed = CASE "
                f"WHEN (places.total_votes + 1) >= {self._min_votes} THEN TRUE "
                f"ELSE places.is_indexed "
                f"END"
            )
            sql_template = f"""
                INSERT INTO places (place_id, name, description, town, type, total_votes, {', '.join(self.FEATURES)})
                VALUES (
                    $1, $2, $3, $4, $5,
                    1, 
                    {', '.join([f'${i+6}' for i in range(len(self.FEATURES))])}
                )
                ON CONFLICT (place_id) DO UPDATE SET
                    {', '.join(set_parts)}
                RETURNING *
            """
            params = [place_id, name, description, town, place_type]
            for field in self.FEATURES:
                params.append(vote_values.get(field, 0.0))
                await conn.fetchrow(sql_template, *params)
        
    async def all_places(self) -> list[dict[str, Any]]:
        columns = ["place_id", "type"] + self.FEATURES
        sql_template = f"""
            SELECT {', '.join(columns)}
            FROM places
            WHERE is_indexed = TRUE
            ORDER BY place_id;
        """
        async with self._db_pool.acquire() as conn:
            conn: Connection
            rows = await conn.fetch(sql_template)
            places_list = []
            for row in rows:
                place_dict = {}
                for column in columns:
                    place_dict[column] = row[column]
                places_list.append(place_dict)
            return places_list
        return []
        
    async def get_meta(self, place_ids: list[int]) -> list[dict[str, Any]]:
        if not place_ids:
            return []
        
        sql_template = """
            SELECT place_id, name, description, town, type
            FROM places
            WHERE place_id = ANY($1::bigint[])
            ORDER BY place_id;
        """
        async with self._db_pool.acquire() as conn:
            conn: Connection
            rows = await conn.fetch(sql_template, place_ids)
            meta_list = []
            for row in rows:
                meta_dict = {
                    "place_id": row["place_id"],
                    "name": row["name"],
                    "description": row["description"],
                    "town": row["town"],
                    "type": row["type"]
                }
                meta_list.append(meta_dict)
            return meta_list
        return []