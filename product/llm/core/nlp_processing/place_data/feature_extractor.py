import os
import json
from typing import Any
from openai import AsyncOpenAI

def load_features():
    with open("features.json", "r") as f:
        return json.load(f)

features_data = load_features()

LLM_NAME = os.getenv("LLM_NAME", "gpt-4o")
CATEGORIES = list(features_data["type"]["categories"].keys())
FEATURE_DESCRIPTIONS = {
    key: value for key, value in features_data.items() 
    if key != "type" and isinstance(value, str)
}

EXTRACTION_PROMPT = f"""
Analyze the user's comment from the text above about a specific rest spot and extract the following information:

Required Information:
1. name: The name/title of the place mentioned by the user
2. description: A concise summary of the user's description of the place
3. town: The town/city where this place is located (extract from context)
4. place_type: The type of place. MUST be exactly one from this list: {', '.join(CATEGORIES)}
5. score: A rating score from 0 to 1 based on user's explicit rating (e.g., "2 stars out of 5" = 0.4, "10/10" = 1.0). If no rating mentioned, infer from sentiment (positive = 0.7-0.9, neutral = 0.5, negative = 0.1-0.3).

Feature Scores (0.0 to 1.0):
For each feature below, assign a score based on the user's description:
{chr(10).join([f"- {key}: {desc}" for key, desc in FEATURE_DESCRIPTIONS.items()])}

If a feature is not mentioned, estimate based on the place_type and description context.

Output Format:
Return ONLY a VALID JSON object with this exact structure:
{{
    "name": "string",
    "description": "string",
    "town": "string",
    "place_type": "string (from categories list)",
    "score": float,
    "features": {{
        {', '.join([f'"{key}": float' for key in FEATURE_DESCRIPTIONS.keys()])}
    }}
}}

Examples:
User: "The Grand Hotel in Paris was fantastic! 5-star luxury, amazing city views but quite expensive. Perfect for couples."
Output: {{
    "name": "The Grand Hotel",
    "description": "Luxury hotel in Paris with amazing city views, expensive but perfect for couples.",
    "town": "Paris",
    "place_type": "hotel",
    "score": 1.0,
    "features": {{
        "natural_scenery": 0.3,
        "cultural_richness": 0.8,
        "adventure_level": 0.2,
        "family_friendliness": 0.4,
        "beach_quality": 0.0,
        "mountain_terrain": 0.0,
        "urban_vibrancy": 0.9,
        "food_variety": 0.7,
        "accommodation_quality": 0.9,
        "transportation_accessibility": 0.8,
        "cost_level": 0.9,
        "safety": 0.8,
        "relaxation_level": 0.7,
        "nightlife_intensity": 0.6,
        "historical_significance": 0.4
    }}
}}
"""

async def get_place_features(client: AsyncOpenAI, messages: list[dict[str, str]]) -> dict[str, Any]:
    try:
        dialogue = messages.copy()
        dialogue.append({
            "role": "system",
            "content": EXTRACTION_PROMPT
        })
        
        response = await client.chat.completions.create(
            model=LLM_NAME,
            messages=dialogue,
            response_format={"type": "json_object"},
            temperature=0.1, 
            max_tokens=1000
        )
        
        output_text = response.choices[0].message.content
        extraction_result = json.loads(output_text)
        name = extraction_result.get("name", "").strip()
        description = extraction_result.get("description", "").strip()
        town = extraction_result.get("town", "").strip()
        place_type = extraction_result.get("place_type", "").lower()
        if place_type not in CATEGORIES:
            for category in CATEGORIES:
                if category in place_type or place_type in category:
                    place_type = category
                    break
            else:
                place_type = CATEGORIES[0] if CATEGORIES else "hotel"
        
        score = float(extraction_result.get("score", 0.5))
        score = max(0.0, min(1.0, score))
        
        features = extraction_result.get("features", {})
        validated_features = {}
        for feature_key in FEATURE_DESCRIPTIONS.keys():
            value = features.get(feature_key, 0.5)
            try:
                float_value = float(value)
                validated_features[feature_key] = max(0.0, min(1.0, float_value))
            except (ValueError, TypeError):
                validated_features[feature_key] = 0.5
        return {
            "status": "ok",
            "name": name if name else "Unnamed Place",
            "description": description if description else "No description provided.",
            "town": town if town else "Unknown",
            "place_type": place_type,
            "score": score,
            "features": validated_features
        }
    except:
        return None