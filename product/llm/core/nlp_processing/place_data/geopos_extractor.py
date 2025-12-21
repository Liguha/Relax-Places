import os
import hashlib
from random import randint
from openai import AsyncOpenAI
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut

__all__ = ["get_place_geopos_id"]

LLM_NAME = os.getenv("LLM_NAME", "gpt-4o")

geolocator = Nominatim(user_agent="rest_points_recsys")

def generate_location_id(lat: float, lon: float) -> int:
    lat_str = f"{lat:.6f}"
    lon_str = f"{lon:.6f}"
    lat_hash = hashlib.sha256(lat_str.encode()).digest()
    lon_hash = hashlib.sha256(lon_str.encode()).digest()
    id_bytes = bytes(a ^ b for a, b in zip(lat_hash[:8], lon_hash[:8]))
    location_id = int.from_bytes(id_bytes, byteorder='big', signed=True)
    return abs(location_id)

PROMPT_TEMPLATE = """
Extract the specific geographic location (town, city, area, street and etc) mentioned in the user's messages above.
First, translate any non-English text to English.
Then, identify and extract only the geographic location that can be geocoded.
You should maximaize location precision.
E.g. if street is not noted, but if is a unique place (e.g. some monument, metro and etc.) then you should use your own knowledges to get more precise address.

Examples:
- "I were in the New-York city " → "New-York, USA"
- "Я был в отеле в Москве" → "Moscow, Russia"

Return ONLY the location string in English, nothing else.
If no location is mentioned make a best proposal.
"""

async def get_place_geopos_id(client: AsyncOpenAI, messages: list[dict[str, str]]) -> int:
    try:
        user_messages = [msg for msg in messages if msg.get("role") == "user"]
        if not user_messages:
            return 0
        user_messages.append({"role": "system", "content": PROMPT_TEMPLATE})
        response = await client.chat.completions.create(
            model=LLM_NAME,
            messages=user_messages,
            temperature=0.1,
            max_tokens=100
        )
        
        extracted_location = response.choices[0].message.content.strip()
        if extracted_location.lower() == "unknown" or not extracted_location:
            return randint(0, 10**9)
        try:
            location = geolocator.geocode(extracted_location, timeout=10)
            if location:
                location_id = generate_location_id(location.latitude, location.longitude)
                return location_id
        except GeocoderTimedOut:
            try:
                simple_location = extracted_location.split(',')[0].strip()
                location = geolocator.geocode(simple_location, timeout=5)
                if location:
                    location_id = generate_location_id(location.latitude, location.longitude)
                    return location_id
            except:
                return randint(0, 10**9)
    except:
        return randint(0, 10**9)