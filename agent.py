import logging
import os

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field


MODEL_ID = "global.anthropic.claude-sonnet-5"
logger = logging.getLogger(__name__)
app = FastAPI(title="Strands Sonnet 5 smoke test")


class Invocation(BaseModel):
    prompt: str = Field(min_length=1, max_length=500)


def invoke(prompt: str) -> dict:
    from strands import Agent, tool
    from strands.models import BedrockModel

    used_multiply = False

    @tool
    def multiply(a: int, b: int) -> int:
        """Multiply two integers.

        Args:
            a: First integer.
            b: Second integer.
        """
        nonlocal used_multiply
        used_multiply = True
        return a * b

    model = BedrockModel(
        model_id=MODEL_ID,
        region_name=os.getenv("AWS_REGION") or os.getenv("AWS_DEFAULT_REGION") or "us-east-1",
        max_tokens=256,
    )
    agent = Agent(
        model=model,
        tools=[multiply],
        system_prompt="Answer briefly. Use the multiply tool for multiplication.",
        callback_handler=None,
    )
    response = str(agent(prompt)).strip()
    if not response:
        raise RuntimeError("Strands returned no text")
    return {"model": MODEL_ID, "response": response, "multiply_used": used_multiply}


@app.get("/ping")
def ping() -> dict:
    return {"status": "healthy", "model": MODEL_ID}


@app.post("/invocations")
def run(body: Invocation) -> dict:
    prompt = body.prompt.strip()
    if not prompt:
        raise HTTPException(status_code=422, detail="Prompt must not be blank")

    try:
        return invoke(prompt)
    except Exception as exc:
        provider_response = getattr(exc, "response", {})
        error_code = provider_response.get("Error", {}).get("Code", type(exc).__name__)
        logger.error("Sonnet 5 invocation failed (%s)", error_code)
        raise HTTPException(status_code=502, detail={"code": error_code}) from exc
