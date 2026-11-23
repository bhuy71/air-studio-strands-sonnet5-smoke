import logging
import os
from urllib.parse import urlsplit

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field


MODEL_ID = "global.anthropic.claude-sonnet-5"
logger = logging.getLogger(__name__)
app = FastAPI(title="Strands Sonnet 5 smoke test")


class ModelProxyConfigurationError(RuntimeError):
    pass


class Invocation(BaseModel):
    prompt: str = Field(min_length=1, max_length=500)
    streaming: bool = True


def air_model(*, streaming: bool):
    import boto3
    from botocore import UNSIGNED
    from botocore.config import Config
    from botocore.session import Session
    from strands.models import BedrockModel

    proxy_url = os.getenv("AIR_MODEL_PROXY_URL", "").strip().rstrip("/")
    token = os.getenv("AIR_MODEL_PROXY_TOKEN", "").strip()
    auth = os.getenv("AIR_MODEL_PROXY_AUTH", "").strip()
    if not proxy_url or not token or auth not in {"bearer", "air_api_key"}:
        raise ModelProxyConfigurationError("AIR_MODEL_PROXY_URL, AIR_MODEL_PROXY_TOKEN and AIR_MODEL_PROXY_AUTH are required")

    proxy = urlsplit(proxy_url)
    if proxy.scheme != "https" or not proxy.hostname or proxy.username or proxy.query or proxy.fragment:
        raise ModelProxyConfigurationError("AIR_MODEL_PROXY_URL must be the HTTPS Model Proxy Endpoint URL")

    header, value = ("Authorization", f"Bearer {token}") if auth == "bearer" else ("AIR-Api-Key", token)

    def attach_air_auth(request, **_kwargs):
        target = urlsplit(request.url)
        if (target.scheme, target.netloc) != (proxy.scheme, proxy.netloc):
            raise RuntimeError("AIR Model Proxy request changed origin")
        request.headers[header] = value

    session = Session()
    session.register("before-send.bedrock-runtime.*", attach_air_auth)
    return BedrockModel(
        boto_session=boto3.Session(botocore_session=session, region_name="ap-northeast-2"),
        boto_client_config=Config(
            signature_version=UNSIGNED,
            connect_timeout=5,
            read_timeout=25,
            retries={"total_max_attempts": 1},
        ),
        endpoint_url=proxy_url,
        model_id=MODEL_ID,
        max_tokens=256,
        streaming=streaming,
    )


def invoke(prompt: str, *, streaming: bool = True) -> dict:
    from strands import Agent, tool

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

    agent = Agent(
        model=air_model(streaming=streaming),
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
    configured = bool(
        os.getenv("AIR_MODEL_PROXY_URL", "").strip()
        and os.getenv("AIR_MODEL_PROXY_TOKEN", "").strip()
        and os.getenv("AIR_MODEL_PROXY_AUTH", "").strip() in {"bearer", "air_api_key"}
    )
    return {
        "status": "healthy",
        "model": MODEL_ID,
        "provider": "air_model_proxy",
        "proxy_configured": configured,
    }


@app.post("/invocations")
@app.post("/internal/resources/{resource_id}/invocations", include_in_schema=False)
def run(body: Invocation) -> dict:
    prompt = body.prompt.strip()
    if not prompt:
        raise HTTPException(status_code=422, detail="Prompt must not be blank")

    try:
        return invoke(prompt, streaming=body.streaming)
    except ModelProxyConfigurationError as exc:
        raise HTTPException(
            status_code=503, detail={"code": "AIR_MODEL_PROXY_NOT_CONFIGURED", "message": str(exc)}
        ) from exc
    except Exception as exc:
        provider_response = getattr(exc, "response", {})
        provider_error = provider_response.get("Error", {})
        error_code = provider_error.get("Code", type(exc).__name__)
        upstream_status = provider_response.get("ResponseMetadata", {}).get("HTTPStatusCode")
        detail = {"code": error_code, "proxy_http_status": upstream_status}
        logger.error("AIR Model Proxy request failed (%s, HTTP %s)", error_code, upstream_status)
        raise HTTPException(status_code=502, detail=detail) from exc
