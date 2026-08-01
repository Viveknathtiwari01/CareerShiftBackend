import os
import json
import asyncio
from anthropic import AsyncAnthropic
import traceback

# If you have a settings module, you can import it here, or load from .env directly.
# Since this is a standalone script, we'll try to use the project's settings.
try:
    from app.core.config import settings
    api_key = settings.ANTHROPIC_API_KEY
except ImportError:
    # Fallback if run completely outside the project context
    api_key = os.getenv("ANTHROPIC_API_KEY")

async def test_connection():
    print("--- Testing Anthropic Connection ---")
    
    if not api_key:
        print("ERROR: ANTHROPIC_API_KEY is not set.")
        return
        
    masked_key = api_key[:7] + "********" if api_key.startswith("sk-") else api_key[:4] + "****"
    print(f"API Key loaded: {masked_key}")
    
    model = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-5")
    print(f"Model configured: {model}")
    
    client = AsyncAnthropic(api_key=api_key)
    
    try:
        print("Sending prompt...")
        response = await client.messages.create(
            model=model,
            max_tokens=100,
            messages=[
                {
                    "role": "user",
                    "content": 'Reply only with:\n{"status":"ok"}'
                }
            ]
        )
        print("Request successful!")
        
        raw_output = response.content[0].text
        print(f"Raw API response: {raw_output}")
        
    except Exception as e:
        print("--- Exception Occurred ---")
        print(f"Exception type: {type(e)}")
        print(f"Exception message: {str(e)}")
        if hasattr(e, 'response') and hasattr(e.response, 'text'):
            print(f"Raw error response body: {e.response.text}")
        print("Stack trace:")
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_connection())
