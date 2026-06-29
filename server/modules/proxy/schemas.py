
from pydantic import BaseModel


class ChatCompletionRequest(BaseModel):
    model: str = "auto"
    messages: list[dict]
    stream: bool = False
    temperature: float | None = None
    max_tokens: int | None = None
    top_p: float | None = None
    tools: list[dict] | None = None
    tool_choice: str | dict | None = None
    parallel_tool_calls: bool | None = None


class ImageGenerationRequest(BaseModel):
    prompt: str
    n: int | None = 1
    model: str | None = None
    size: str | None = "1024x1024"
    quality: str | None = "standard"
    style: str | None = "vivid"
    response_format: str | None = "url"
