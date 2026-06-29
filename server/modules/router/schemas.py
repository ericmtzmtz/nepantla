
from pydantic import BaseModel


class RouteResult(BaseModel):
    platform: str
    model_id: str
    provider_name: str
    api_key_id: int
    sticky: bool = False


class PoolType:
    CHAT = "chat"
    VISION = "vision"
    IMAGE_GEN = "image_gen"
    AUDIO = "audio"
    EMBED = "embed"
    CHAT_TOOLS = "chat_tools"
