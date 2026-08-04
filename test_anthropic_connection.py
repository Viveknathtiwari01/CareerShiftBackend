import asyncio
import traceback

from anthropic import AuthenticationError, APIStatusError

from app.core.anthropic_client import (
    create_async_client,
    get_anthropic_model,
    get_anthropic_temperature,
)


async def test_connection():
    print("--- Testing Anthropic Connection ---")
    print(f"Model configured: {get_anthropic_model()}")
    print(f"Temperature: {get_anthropic_temperature()}")

    try:
        client = create_async_client()
    except ValueError as exc:
        print(f"ERROR: {exc}")
        return

    try:
        print("Sending prompt...")
        response = await client.messages.create(
            model=get_anthropic_model(),
            max_tokens=100,
            temperature=get_anthropic_temperature(),
            messages=[
                {
                    "role": "user",
                    "content": 'Reply only with:\n{"status":"ok"}',
                }
            ],
        )
        print("Request successful!")
        print(f"Raw API response: {response.content[0].text}")

    except AuthenticationError as e:
        print("--- Authentication Error (401) ---")
        print("The ANTHROPIC_API_KEY in Backend/.env is invalid or revoked.")
        print(f"Detail: {e}")
    except APIStatusError as e:
        print(f"--- API Error ({e.status_code}) ---")
        print(f"Detail: {e.message}")
        if e.status_code == 400 and "credit balance" in (e.message or "").lower():
            print("\nKey is VALID but account has no credits.")
            print("Add credits: https://console.anthropic.com/settings/billing")
    except Exception as e:
        print("--- Exception Occurred ---")
        print(f"Exception type: {type(e)}")
        print(f"Exception message: {str(e)}")
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_connection())
