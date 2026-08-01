import json
import os
from anthropic import AsyncAnthropic
import logging

from app.core.config import settings
from prompts import SYSTEM_PROMPT, USER_PROMPT_TEMPLATE

logger = logging.getLogger(__name__)

client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)

async def generate_skills_from_ai(
    job_title: str,
    industry: str,
    business_function: str,
    functional_domain: str,
    specialization: str,
    experience: str,
) -> dict:
    """
    Calls Anthropic to generate 5 sets of skills based on the user's profile context.
    Returns a dictionary matching the 5 JSON categories.
    """
    user_prompt = USER_PROMPT_TEMPLATE.format(
        job_title=job_title,
        industry=industry,
        business_function=business_function,
        functional_domain=functional_domain,
        specialization=specialization,
        experience=experience,
    )

    try:
        api_key = settings.ANTHROPIC_API_KEY
        if not api_key:
            logger.error("ANTHROPIC_API_KEY is missing or empty.")
            raise ValueError("ANTHROPIC_API_KEY is not set.")
        else:
            masked_key = api_key[:7] + "********" if api_key.startswith("sk-") else api_key[:4] + "****"
            logger.info(f"ANTHROPIC_API_KEY: {masked_key}")

        model = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-5")
        logger.info(f"Using Anthropic model: {model}")
            
        try:
            response = await client.messages.create(
                model=model,
                max_tokens=2048,
                system=SYSTEM_PROMPT,
                messages=[
                    {
                        "role": "user",
                        "content": user_prompt,
                    },
                ]
            )
        except Exception as e:
            logger.exception("Error generating AI skills - API request failed")
            if hasattr(e, 'response') and hasattr(e.response, 'text'):
                logger.error(f"Raw API Response: {e.response.text}")
            raise e
        
        output_text = response.content[0].text
        logger.info(f"Raw model output before parsing: {output_text}")
        
        output_text = output_text.strip()
        # Strip out any potential markdown blocks if the model outputs ```json ... ```
        if output_text.startswith("```"):
            lines = output_text.splitlines()
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines[-1].startswith("```"):
                lines = lines[:-1]
            output_text = "\n".join(lines)
            
        try:
            parsed_skills = json.loads(output_text)
        except Exception as e:
            logger.error("Failed to parse JSON response.")
            logger.error(f"Raw response: {output_text}")
            logger.error(f"Parsing exception: {str(e)}")
            logger.error(f"Response content type: {type(output_text)}")
            raise e

        return parsed_skills

    except Exception as e:
        logger.exception("Error generating AI skills")
        # Fallback empty structure in case of parsing/API failure
        return {
            "technicalSkills": [],
            "professionalSkills": [],
            "softSkills": [],
            "behaviouralSkills": [],
            "digitalSkills": [],
            "aiTools": []
        }
