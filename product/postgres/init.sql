CREATE TABLE users (
    user_id VARCHAR(100) PRIMARY KEY,
    unprocessed_votes INT DEFAULT 0,
    total_votes INT DEFAULT 0
);

CREATE TABLE places (
    place_id BIGINT PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    town VARCHAR(255) NOT NULL,
    type VARCHAR(255) NOT NULL,
    
    natural_scenery FLOAT DEFAULT 0.00,
    cultural_richness FLOAT DEFAULT 0.00,
    adventure_level FLOAT DEFAULT 0.00,
    family_friendliness FLOAT DEFAULT 0.00,
    beach_quality FLOAT DEFAULT 0.00,
    mountain_terrain FLOAT DEFAULT 0.00,
    urban_vibrancy FLOAT DEFAULT 0.00,
    food_variety FLOAT DEFAULT 0.00,
    accommodation_quality FLOAT DEFAULT 0.00,
    transportation_accessibility FLOAT DEFAULT 0.00,
    cost_level FLOAT DEFAULT 0.00,
    safety FLOAT DEFAULT 0.00,
    relaxation_level FLOAT DEFAULT 0.00,
    nightlife_intensity FLOAT DEFAULT 0.00,
    historical_significance FLOAT DEFAULT 0.00,
    
    total_votes INT DEFAULT 0,
    is_indexed BOOLEAN DEFAULT FALSE
);

CREATE TABLE votes (
    vote_id SERIAL PRIMARY KEY,
    user_id VARCHAR(100) NOT NULL,
    place_id BIGINT NOT NULL,
    score FLOAT NOT NULL,

    CONSTRAINT unique_user_place_reals UNIQUE (user_id, place_id)
);

CREATE TABLE virtual_scores (
    vote_id SERIAL PRIMARY KEY,
    user_id VARCHAR(100) NOT NULL,
    place_id BIGINT NOT NULL,
    score FLOAT NOT NULL,

    CONSTRAINT unique_user_place_virtuals UNIQUE (user_id, place_id)
);