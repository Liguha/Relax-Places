import os
from typing import Any
from copy import copy
from openai import AsyncOpenAI

__all__ = ["get_messages_type"]

LLM_NAME = os.getenv("LLM_NAME", "gpt-4o")

INSTRUCTION = ""\
"Based on the previous dialogue (mostly on the last messages) select type of the user request. Allowed types: `comment`, `recommend`, `other`. "\
"`comment` stand for commenting some certain rest spot. "\
"`recommend` stand for request of the recommendation from the bot. "\
"Use `other` in the case when it is impossible to determine category (neither `comment` nor `recommend`). "\
"Print EXACTLY 1 word - determined type without any quotes."

async def get_messages_type(client: AsyncOpenAI, messages: list[dict[str, Any]]) -> str:
    try:
        dialogue = copy(messages)
        dialogue.append({
            "role": "system",
            "content": INSTRUCTION
        })
        response = await client.chat.completions.create(
            model=LLM_NAME,
            messages=dialogue,
            response_format={"type": "json_object"}
        )
        output_text = response.choices[0].message.content
        if output_text != "comment" and output_text != "recommend":
            output_text = "other"
        return output_text
    except:
        return "other"