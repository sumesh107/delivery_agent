from typing import Any

from langchain_core.callbacks import BaseCallbackHandler


class DebugCallbackHandler(BaseCallbackHandler):
    def on_llm_start(self, serialized: dict[str, Any], prompts: list[str], **kwargs: Any) -> None:
        print("[LLM] start")
        for prompt in prompts:
            print(prompt)

    def on_llm_end(self, response: Any, **kwargs: Any) -> None:
        print("[LLM] end")
        print(response)
