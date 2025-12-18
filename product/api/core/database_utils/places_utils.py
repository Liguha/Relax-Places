from typing import ClassVar
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

    async def upsert_place(self, place_id: int, name: str, town: str, place_type: str, vote_values: dict[str, float]) -> None:
        async with self._db_pool.acquire() as conn:
            conn: Connection
            set_parts = [
                "name = EXCLUDED.name",
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
                INSERT INTO places (place_id, name, town, type, total_votes, {', '.join(self.FEATURES)})
                VALUES (
                    $1, $2, $3, $4, 
                    1, 
                    {', '.join([f'${i+5}' for i in range(len(self.FEATURES))])}
                )
                ON CONFLICT (place_id) DO UPDATE SET
                    {', '.join(set_parts)}
                RETURNING *
            """
            params = [place_id, name, town, place_type]
            for field in self.FEATURES:
                params.append(vote_values.get(field, 0.0))
            return await conn.fetchrow(sql_template, *params)