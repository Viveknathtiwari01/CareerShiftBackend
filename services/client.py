import os
import json
import logging
import time
from typing import Dict, Any, Callable
from anthropic import Anthropic, APIStatusError

from app.core.anthropic_client import (
    build_messages_create_kwargs,
    create_sync_client,
    get_anthropic_model,
    get_anthropic_temperature,
)

# Configure basic logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

client = create_sync_client()
MODEL_NAME = get_anthropic_model()
TEMPERATURE = get_anthropic_temperature()


def extract_text(response: Any) -> str:
    """Extracts only text blocks from the Anthropic response, ignoring Thinking or Tool blocks."""
    response_text = ""
    for block in response.content:
        b_type = getattr(block, 'type', type(block).__name__)
        if b_type == 'text':
            response_text += getattr(block, 'text', '')
    return response_text


def strip_markdown(text: str) -> str:
    """Removes markdown formatting fences from the text."""
    clean_text = text.strip()
    if clean_text.startswith("```json"):
        clean_text = clean_text[7:]
    elif clean_text.startswith("```"):
        clean_text = clean_text[3:]
        
    if clean_text.endswith("```"):
        clean_text = clean_text[:-3]
        
    return clean_text.strip()


def extract_json(text: str) -> str:
    """Finds the JSON boundaries in case there is trailing or leading text."""
    start_idx = text.find('{')
    arr_idx = text.find('[')
    
    # Check if it starts with array or object
    if start_idx == -1 and arr_idx == -1:
        return text
        
    if start_idx != -1 and (arr_idx == -1 or start_idx < arr_idx):
        start = start_idx
        end = text.rfind('}') + 1
    else:
        start = arr_idx
        end = text.rfind(']') + 1
        
    if start != -1 and end != 0:
        return text[start:end]
    return text


def validate_json(text: str) -> None:
    """Validates that the text is not empty and seems to be complete."""
    if not text:
        raise ValueError("The extracted text is empty.")


def parse_json(text: str) -> Dict[str, Any]:
    """Attempts to parse the JSON, raising a detailed ValueError on failure."""
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        logger.error("Failed to parse JSON.")
        logger.error(f"Raw extracted text:\n{text}")
        logger.error(f"Exception details: {str(e)}")
        raise ValueError(f"Failed to parse JSON response from Claude.\nExtracted Text: {text}") from e


def retry_request(func: Callable, max_retries: int = 3, delay: float = 2.0) -> Any:
    """Retries a function call if it raises an exception."""
    last_exception = None
    for attempt in range(max_retries):
        try:
            return func()
        except Exception as e:
            last_exception = e
            logger.warning(f"Attempt {attempt + 1}/{max_retries} failed: {e}")
            if attempt < max_retries - 1:
                time.sleep(delay)
    raise last_exception


def call_anthropic(system_prompt: str, user_prompt: str) -> Dict[str, Any]:
    """
    Calls the Anthropic API and safely extracts structured JSON.
    Maintains the exact public API required.
    """
    def _make_api_call():
        request_kwargs = build_messages_create_kwargs(
            MODEL_NAME,
            max_tokens=8192,
            temperature=TEMPERATURE,
            system=system_prompt,
            messages=[
                {
                    "role": "user",
                    "content": user_prompt
                }
            ],
        )
        response = client.messages.create(**request_kwargs)
        
        response_text = extract_text(response)
        block_types = [getattr(b, 'type', type(b).__name__) for b in response.content]
        
        char_count = len(response_text)
        first_500 = response_text[:500] if char_count > 0 else ""
        last_500 = response_text[-500:] if char_count > 500 else response_text
        
        logger.info(f"Model: {MODEL_NAME}")
        logger.info(f"Stop Reason: {response.stop_reason}")
        if hasattr(response, 'usage'):
            logger.info(f"Usage: input_tokens={getattr(response.usage, 'input_tokens', 'N/A')}, output_tokens={getattr(response.usage, 'output_tokens', 'N/A')}")
        logger.info(f"Response block types: {', '.join(block_types)}")
        logger.info(f"Response character count: {char_count}")
        logger.info(f"First 500 characters:\n{first_500}")
        logger.info(f"Last 500 characters:\n{last_500}")
        
        if not response_text:
            raise ValueError(f"Claude returned reasoning blocks but no text response. (Stop reason: {response.stop_reason}, Blocks: {block_types})")
            
        if response.stop_reason in ["max_tokens", "length"]:
            raise ValueError(f"Claude response was truncated because max_tokens was reached (stop_reason: '{response.stop_reason}').")
            
        clean_text = strip_markdown(response_text)
        json_text = extract_json(clean_text)
        validate_json(json_text)
        
        return parse_json(json_text)
        
    return retry_request(_make_api_call, max_retries=3)
