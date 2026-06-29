
from pydantic import BaseModel, ConfigDict


class ChatMessage(BaseModel):
    role: str
    content: str | list[dict]


class CompletionOptions(BaseModel):
    temperature: float | None = None
    max_tokens: int | None = None
    top_p: float | None = None
    stream: bool = False
    tools: list[dict] | None = None
    tool_choice: str | dict | None = None
    parallel_tool_calls: bool | None = None


class ChatCompletionResponse(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: list[dict]
    usage: dict | None = None


class ChatCompletionChunk(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    id: str
    object: str = "chat.completion.chunk"
    created: int
    model: str
    choices: list[dict]


class ImageGenOptions(BaseModel):
    model: str | None = None
    n: int | None = 1
    size: str | None = "1024x1024"
    quality: str | None = "standard"
    style: str | None = "vivid"
    response_format: str | None = "url"


class ImageGenResponse(BaseModel):
    created: int
    data: list[dict]


class AudioTranscriptionOptions(BaseModel):
    language: str | None = None


class TranscriptionResponse(BaseModel):
    text: str


class TextToSpeechOptions(BaseModel):
    voice: str | None = "alloy"
    speed: float | None = 1.0
    response_format: str | None = "wav"


class ModelInfo(BaseModel):
    id: str
    platform: str
    display_name: str = ""
    supports_vision: bool = False
    supports_image_gen: bool = False
    supports_audio_stt: bool = False
    supports_audio_tts: bool = False
    supports_embeddings: bool = False
