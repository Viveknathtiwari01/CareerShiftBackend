import asyncio
import traceback

from anthropic import AuthenticationError, APIStatusError

from app.core.anthropic_client import (
    build_messages_create_kwargs,
    create_async_client,
    get_anthropic_effort,
    get_anthropic_model,
    get_anthropic_temperature,
    model_supports_sampling_params,
)


async def test_connection():
    print("--- Testing Anthropic Connection ---")
    model = get_anthropic_model()
    print(f"Model configured: {model}")
    if model_supports_sampling_params(model):
        print(f"Temperature: {get_anthropic_temperature()}")
    else:
        print(f"Effort: {get_anthropic_effort()} (temperature not supported for this model)")

    try:
        client = create_async_client()
    except ValueError as exc:
        print(f"ERROR: {exc}")
        return

    try:
        print("Sending prompt...")
        request_kwargs = build_messages_create_kwargs(
            model,
            max_tokens=100,
            temperature=get_anthropic_temperature(),
            messages=[
                {
                    "role": "user",
                    "content": 'Reply only with:\n{"status":"ok"}',
                }
            ],
        )
        response = await client.messages.create(**request_kwargs)
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
