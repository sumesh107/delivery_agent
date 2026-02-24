import inspect
import os
from typing import Any

from config import apply_ai_core_env


def build_llm() -> Any:
    apply_ai_core_env()
    model_name = os.getenv("LLM_MODEL_NAME", "gpt-4o")
    deployment_id = os.getenv("LLM_DEPLOYMENT_ID", "d7c46acfaeca52aa")
    from gen_ai_hub.proxy.langchain.init_models import init_llm

    if os.getenv("ORCH_DEBUG", "0") == "1":
        print(f"[LLM] using model_name={model_name} deployment_id={deployment_id}")

    signature = inspect.signature(init_llm)
    extra_kwargs = {"deployment_id": deployment_id} if deployment_id else {}
    max_tokens = int(os.getenv("LLM_MAX_COMPLETION_TOKENS", "2048"))
    reasoning_effort = os.getenv("LLM_REASONING_EFFORT", "low")
    model_kwargs = {"max_completion_tokens": max_tokens}
    if reasoning_effort:
        model_kwargs["reasoning_effort"] = reasoning_effort
    try:
        if "model_kwargs" in signature.parameters:
            extra_kwargs["model_kwargs"] = model_kwargs
        elif "reasoning_effort" in signature.parameters and reasoning_effort:
            extra_kwargs["reasoning_effort"] = reasoning_effort
        if "model_name" in signature.parameters:
            return init_llm(model_name=model_name, **extra_kwargs)
        if "model" in signature.parameters:
            return init_llm(model=model_name, **extra_kwargs)
        return init_llm(model_name, **extra_kwargs)
    except KeyError:
        from gen_ai_hub.proxy.langchain.openai import ChatOpenAI

        return ChatOpenAI(
            deployment_id=deployment_id,
            temperature=0.2,
            model_kwargs=model_kwargs,
        )
