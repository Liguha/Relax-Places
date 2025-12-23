from typing import Any
from asyncpg import Connection, Pool
import pandas as pd
import numpy as np
from pathlib import Path
from catboost import CatBoostRegressor

__all__ = ["train_model"]

# Фичи, используемые в модели
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


async def train_model(db_pool: Pool, model_path: str = "/models/model.cbm", seed: int = 228) -> None:
    """
    Обучает CatBoost модель на данных из базы данных.
    """
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
    
    async with db_pool.acquire() as conn:
        conn: Connection
        rows = await conn.fetch(sql_template)
    
    if not rows:
        raise ValueError("No data available for training")
    
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
    train_raw, _ = make_split_leave1out(df, seed=seed)
    user_prof = build_user_profile(train_raw)
    train = add_features(train_raw, user_prof)
    
    # Подготовка признаков и целевой переменной
    feat_cols = get_feature_cols()
    X_train, y_train = train[feat_cols], train["rating"].astype(float)
    
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

    # Сохранение модели
    model_path_obj = Path(model_path)
    model_path_obj.parent.mkdir(parents=True, exist_ok=True)
    model.save_model(str(model_path_obj))