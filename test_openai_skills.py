import json
import logging
from app.core.anthropic_client import (
    build_messages_create_kwargs,
    create_sync_client,
    extract_response_text,
    get_active_provider,
    get_anthropic_model,
    get_anthropic_temperature,
)
from prompts import SYSTEM_PROMPT, USER_PROMPT_TEMPLATE

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")


def generate_skills(
    job_title: str,
    industry: str,
    business_function: str,
    functional_domain: str,
    specialization: str,
    experience: str,
) -> str:
    user_prompt = USER_PROMPT_TEMPLATE.format(
        job_title=job_title,
        industry=industry,
        business_function=business_function,
        functional_domain=functional_domain,
        specialization=specialization,
        experience=experience,
    )

    client = create_sync_client()
    model = get_anthropic_model()
    temperature = get_anthropic_temperature()

    request_kwargs = build_messages_create_kwargs(
        model,
        max_tokens=2048,
        temperature=temperature,
        system=SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": user_prompt,
            }
        ],
    )

    response = client.messages.create(**request_kwargs)
    return extract_response_text(response)


def main():
    provider = get_active_provider()
    model = get_anthropic_model()
    print(f"\n========== CareerShift AI Skill Generator (Provider: {provider.upper()}, Model: {model}) ==========\n")

    job_title = input("Current Job Title: ") or "Software Engineer"
    industry = input("Industry: ") or "Technology"
    business_function = input("Business Function: ") or "Engineering"
    functional_domain = input("Functional Domain: ") or "Software Development"
    specialization = input("Specialization: ") or "Full Stack Development"
    experience = input("Total Experience: ") or "5 years"

    print("\nGenerating skills...\n")

    result = generate_skills(
        job_title,
        industry,
        business_function,
        functional_domain,
        specialization,
        experience,
    )

    try:
        parsed = json.loads(result)
        print("\n========== AI Response ==========\n")
        print(json.dumps(parsed, indent=4))
    except Exception:
        print("\nRaw Response\n")
        print(result)


if __name__ == "__main__":
    main()