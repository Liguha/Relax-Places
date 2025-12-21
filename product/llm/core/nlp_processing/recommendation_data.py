import json
import os
from openai import AsyncOpenAI

__all__ = ["get_recommendation_data"]

features: dict
with open("features.json", "r") as f:
    features = json.load(f)

ALLOWED_TYPES = features.get("types", {})
LLM_NAME = os.getenv("LLM_NAME", "gpt-4o")

EXTRACTION_INSTRUCTION = f"""Analyze the dialogue above and extract two pieces of information:

1. Allowed Towns: List all towns/cities/locations the user is explicitly looking for spots in. Return as a list.
2. Allowed Types: List all types of rest spots the user is interested in. You MUST ONLY use types from this exact dict:

{', '.join(ALLOWED_TYPES)}

Rules:
- If the user mentions specific towns (e.g., "in Moscow", "near Paris"), extract them
- If the user mentions spot types (e.g., "hotels", "beaches"), map them to the exact terms from the list above
- If no specific towns are mentioned, return empty list for towns
- If no specific types are mentioned, return empty list for types
- Always return valid JSON with exactly this structure:
{{
  "allowed_towns": ["town1", "town2"],
  "allowed_types": ["type1", "type2"]
}}

Examples:
- User: "I want to find hotels in Moscow" → {{"allowed_towns": ["Moscow"], "allowed_types": ["hotel"]}}
- User: "Show me beaches and restaurants" → {{"allowed_towns": [], "allowed_types": ["beach", "restaurant"]}}
- User: "Any interesting spots?" → {{"allowed_towns": [], "allowed_types": []}}
"""

async def get_recommendation_data(client: AsyncOpenAI, messages: list[dict[str, str]]) -> tuple[list[str], list[str]]:
    try:
        dialogue = messages.copy()
        dialogue.append({
            "role": "system",
            "content": EXTRACTION_INSTRUCTION
        })
        response = await client.chat.completions.create(
            model=LLM_NAME,
            messages=dialogue,
            response_format={"type": "json_object"},
            temperature=0.1
        )
        output_text = response.choices[0].message.content
        extraction_result = json.loads(output_text)
        allowed_towns = extraction_result.get("allowed_towns", [])
        allowed_types = extraction_result.get("allowed_types", [])
        if not isinstance(allowed_towns, list):
            allowed_towns = []
        if not isinstance(allowed_types, list):
            allowed_types = []
        return [str(town).strip() for town in allowed_types if town], [str(town).strip() for town in allowed_towns if town]
    except:
        return [], []