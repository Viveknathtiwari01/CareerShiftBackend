import json
import os

from dotenv import load_dotenv
from openai import OpenAI

from prompts import SYSTEM_PROMPT, USER_PROMPT_TEMPLATE

load_dotenv()

client = OpenAI(
    api_key=os.getenv("ANTHROPIC_API_KEY")
)

MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4")


def generate_skills(
    job_title,
    industry,
    business_function,
    functional_domain,
    specialization,
    experience,
):
    user_prompt = USER_PROMPT_TEMPLATE.format(
        job_title=job_title,
        industry=industry,
        business_function=business_function,
        functional_domain=functional_domain,
        specialization=specialization,
        experience=experience,
    )

    response = client.responses.create(
        model=MODEL,
        temperature=0.2,
        input=[
            {
                "role": "system",
                "content": SYSTEM_PROMPT,
            },
            {
                "role": "user",
                "content": user_prompt,
            },
        ],
    )

    return response.output_text


def main():
    print("\n========== CareerShift AI Skill Generator ==========\n")

    job_title = input("Current Job Title: ")
    industry = input("Industry: ")
    business_function = input("Business Function: ")
    functional_domain = input("Functional Domain: ")
    specialization = input("Specialization: ")
    experience = input("Total Experience: ")

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