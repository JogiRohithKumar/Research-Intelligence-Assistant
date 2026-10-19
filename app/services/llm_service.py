"""
Structured LLM Service for Research Intelligence Assistant V2.
Uses the modern Google GenAI SDK (google-genai) with Pydantic response schemas
and graceful multi-stage validation, sanitization, and retry fallback.
"""

import json
import re
from typing import Any, Dict, Optional, Type, TypeVar
from pydantic import BaseModel, ValidationError

from google import genai
from google.genai import types

from app.core.config import get_settings
from app.core.exceptions import LLMGenerationError, LLMValidationError
from app.core.logging import logger

T = TypeVar("T", bound=BaseModel)


def get_genai_client() -> genai.Client:
    """Instantiate a Google GenAI client from centralized settings."""
    settings = get_settings()
    if settings.GEMINI_API_KEY:
        return genai.Client(api_key=settings.GEMINI_API_KEY)
    return genai.Client()


def sanitize_raw_json(text: str) -> str:
    """
    Cleans raw LLM text to extract parseable JSON.
    Handles markdown fences (```json ... ```), trailing commas, and leading commentary.
    """
    text = text.strip()
    if not text:
        return "{}"

    # Strip markdown code blocks
    if text.startswith("```"):
        lines = text.splitlines()
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()

    # If it directly parses, return
    try:
        json.loads(text)
        return text
    except Exception:
        pass

    # Extract outermost balanced { ... } or [ ... ]
    match_object = re.search(r"(\{[\s\S]*\})", text)
    match_array = re.search(r"(\[[\s\S]*\])", text)

    # Prefer whichever match starts earlier
    candidates = []
    if match_object:
        candidates.append((match_object.start(), match_object.group(1)))
    if match_array:
        candidates.append((match_array.start(), match_array.group(1)))

    if candidates:
        candidates.sort(key=lambda x: x[0])
        best_candidate = candidates[0][1]
        try:
            json.loads(best_candidate)
            return best_candidate
        except Exception:
            return best_candidate

    return text


def generate_structured_output(
    prompt: str,
    schema: Type[T],
    system_instruction: Optional[str] = None,
    max_retries: int = 2,
    model: Optional[str] = None,
) -> T:
    """
    Calls Gemini using modern google-genai structured output with Pydantic schema validation.
    Gracefully handles invalid formatting, missing fields, and retries on failure.
    """
    settings = get_settings()
    target_model = model or settings.GEMINI_MODEL
    client = get_genai_client()

    current_prompt = prompt
    last_error: Optional[Exception] = None

    for attempt in range(max_retries + 1):
        try:
            config = types.GenerateContentConfig(
                temperature=settings.LLM_TEMPERATURE,
                max_output_tokens=settings.LLM_MAX_OUTPUT_TOKENS,
                response_mime_type="application/json",
                response_schema=schema,
            )
            if system_instruction:
                config.system_instruction = system_instruction

            response = client.models.generate_content(
                model=target_model,
                contents=current_prompt,
                config=config,
            )

            raw_text = response.text or ""
            if not raw_text.strip():
                raise LLMGenerationError("Empty response returned from LLM provider")

            # First attempt: Direct model validation
            try:
                validated_model = schema.model_validate_json(raw_text)
                return validated_model
            except ValidationError as ve:
                logger.warning(
                    f"Direct schema validation failed on attempt {attempt + 1}. Attempting sanitization. Error: {ve}"
                )

            # Second attempt: Sanitize and parse
            sanitized = sanitize_raw_json(raw_text)
            try:
                parsed_dict = json.loads(sanitized)
                # If schema is an array wrapper but response is array, wrap it
                if hasattr(schema, "__fields__") or hasattr(schema, "model_fields"):
                    # Check if schema has a single list field matching array
                    fields = getattr(schema, "model_fields", getattr(schema, "__fields__", {}))
                    if isinstance(parsed_dict, list) and len(fields) == 1:
                        field_name = next(iter(fields))
                        parsed_dict = {field_name: parsed_dict}

                return schema.model_validate(parsed_dict)
            except (json.JSONDecodeError, ValidationError) as parse_err:
                logger.warning(
                    f"Sanitized JSON validation failed on attempt {attempt + 1}: {parse_err}"
                )
                last_error = parse_err

                # Prepare corrective prompt for retry
                current_prompt = (
                    f"{prompt}\n\n"
                    f"CRITICAL FIX: Your previous response failed schema validation with error: {parse_err}\n"
                    f"You MUST return ONLY valid JSON matching this schema exactly: {json.dumps(schema.model_json_schema())}"
                )

        except Exception as e:
            logger.error(f"LLM API invocation error on attempt {attempt + 1}: {e}")
            last_error = e
            err_msg = str(e)
            if "RESOURCE_EXHAUSTED" in err_msg or "429" in err_msg:
                break

    raise LLMValidationError(
        f"Failed to generate valid structured output for schema '{schema.__name__}' after {max_retries + 1} attempts. Last error: {last_error}"
    )


def generate_text(
    prompt: str,
    system_instruction: Optional[str] = None,
    model: Optional[str] = None,
) -> str:
    """Generates freeform text using the Gemini model."""
    settings = get_settings()
    target_model = model or settings.GEMINI_MODEL
    client = get_genai_client()

    config = types.GenerateContentConfig(
        temperature=settings.LLM_TEMPERATURE,
        max_output_tokens=settings.LLM_MAX_OUTPUT_TOKENS,
    )
    if system_instruction:
        config.system_instruction = system_instruction

    try:
        response = client.models.generate_content(
            model=target_model,
            contents=prompt,
            config=config,
        )
        return (response.text or "").strip()
    except Exception as e:
        logger.error(f"Text generation failed: {e}")
        raise LLMGenerationError(f"LLM text generation failed: {e}") from e
