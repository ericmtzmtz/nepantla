from pydantic import BaseModel


class EmbeddingOptions(BaseModel):
    input: str | list[str]
    model: str
    encoding_format: str | None = None
    dimensions: int | None = None
    input_type: str | None = None  # cohere-specific


class EmbeddingObject(BaseModel):
    object: str = "embedding"
    embedding: list[float]
    index: int


class EmbeddingUsage(BaseModel):
    prompt_tokens: int = 0
    total_tokens: int = 0


class EmbeddingResponse(BaseModel):
    object: str = "list"
    data: list[EmbeddingObject]
    model: str
    usage: EmbeddingUsage = EmbeddingUsage()
