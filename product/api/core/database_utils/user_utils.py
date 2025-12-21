from typing import Any
from asyncpg import Connection, Pool, Record
import pandas as pd
import numpy as np
from pathlib import Path
from catboost import CatBoostRegressor

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
                ON CONFLICT ON CONSTRAINT unique_user_place_reals
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
    
    async def train_model(self, model_path: str = "model.cbm", seed: int = 77) -> dict[str, float]:
        """
        Обучает CatBoost модель на данных из базы данных.
        
        Args:
            model_path: Путь для сохранения модели
            seed: Случайное зерно для воспроизводимости
            
        Returns:
            Словарь с метриками модели (rmse, mae, r2)
        """
        from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
        
        # Используем те же фичи, что и в PlacesWorker
        FEATURES = [
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
        
        # Получаем все данные из базы
        sql_template = """
            SELECT 
                v.user_id,
                v.score as rating,
                p.place_id,
                p.type,
                p.natural_scenery,
                p.cultural_richness,
                p.adventure_level,
                p.family_friendliness,
                p.beach_quality,
                p.mountain_terrain,
                p.urban_vibrancy,
                p.food_variety,
                p.accommodation_quality,
                p.transportation_accessibility,
                p.cost_level,
                p.safety,
                p.relaxation_level,
                p.nightlife_intensity,
                p.historical_significance
            FROM votes v
            INNER JOIN places p ON v.place_id = p.place_id
            WHERE p.is_indexed = TRUE
            ORDER BY v.vote_id;
        """
        
        async with self._db_pool.acquire() as conn:
            conn: Connection
            rows = await conn.fetch(sql_template)
        
        if not rows:
            raise ValueError("No data available for training")
        
        # Преобразуем в DataFrame
        data = []
        for row in rows:
            row_dict = dict(row)
            data.append(row_dict)
        
        df = pd.DataFrame(data)
        
        # Проверяем наличие необходимых колонок
        required = ["user_id", "rating"] + FEATURES
        missing = [c for c in required if c not in df.columns]
        if missing:
            raise KeyError(f"Missing columns: {missing}")
        
        # Функции из notebook
        def make_split_leave1out(df: pd.DataFrame, user_col: str = "user_id", seed: int = 42) -> tuple[pd.DataFrame, pd.DataFrame]:
            rng = np.random.default_rng(seed)
            df = df.copy()
            df["__is_test__"] = False

            for _, g in df.groupby(user_col):
                if len(g) <= 1:
                    continue
                test_idx = rng.choice(g.index.to_numpy(), size=1)[0]
                df.loc[test_idx, "__is_test__"] = True

            mask = df["__is_test__"].astype(bool).to_numpy()
            train = df.loc[~mask].drop(columns="__is_test__")
            test = df.loc[mask].drop(columns="__is_test__")
            return train, test
        
        def build_user_profile(train: pd.DataFrame, user_col: str = "user_id") -> pd.DataFrame:
            agg = {
                "u_mean_rating": ("rating", "mean"),
                "u_std_rating": ("rating", "std"),
                "u_cnt": ("rating", "size"),
            }
            for f in FEATURES:
                agg[f"u_mean_{f}"] = (f, "mean")

            prof = train.groupby(user_col).agg(**agg).reset_index()
            prof["u_std_rating"] = prof["u_std_rating"].fillna(0.0)
            return prof
        
        def add_features(df: pd.DataFrame, user_prof: pd.DataFrame, user_col: str = "user_id") -> pd.DataFrame:
            out = df.merge(user_prof, on=user_col, how="left")

            # Если пользователь вообще не встречался в train — заполним дефолтами
            out["u_cnt"] = out["u_cnt"].fillna(0)
            out["u_mean_rating"] = out["u_mean_rating"].fillna(out["rating"].mean())
            out["u_std_rating"] = out["u_std_rating"].fillna(0.0)

            for f in FEATURES:
                out[f"u_mean_{f}"] = out[f"u_mean_{f}"].fillna(out[f].mean())
                out[f"diff_{f}"] = (out[f].astype(float) - out[f"u_mean_{f}"].astype(float)).abs()

            return out
        
        def get_feature_cols() -> list[str]:
            return FEATURES + [f"diff_{f}" for f in FEATURES] + ["u_cnt", "u_mean_rating", "u_std_rating"]
        
        # Подготовка данных
        train_raw, test_raw = make_split_leave1out(df, seed=seed)
        user_prof = build_user_profile(train_raw)
        train = add_features(train_raw, user_prof)
        test = add_features(test_raw, user_prof)
        
        # Подготовка признаков и целевой переменной
        feat_cols = get_feature_cols()
        X_train, y_train = train[feat_cols], train["rating"].astype(float)
        X_test, y_test = test[feat_cols], test["rating"].astype(float)
        
        # Обучение модели
        model = CatBoostRegressor(
            iterations=1200,
            depth=6,
            learning_rate=0.05,
            loss_function="RMSE",
            random_seed=seed,
            verbose=False
        )
        
        model.fit(X_train, y_train)
        
        # Предсказания и метрики
        pred = model.predict(X_test)
        rmse = mean_squared_error(y_test, pred) ** 0.5
        mae = mean_absolute_error(y_test, pred)
        r2 = r2_score(y_test, pred)
        
        # Сохранение модели
        model_path_obj = Path(model_path)
        model_path_obj.parent.mkdir(parents=True, exist_ok=True)
        model.save_model(str(model_path_obj))
        
        return {"rmse": float(rmse), "mae": float(mae), "r2": float(r2)}