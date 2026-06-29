def content_to_string(content: str | list[dict]) -> str:
    """Extract text from content blocks (handles vision messages with image_url)."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if block.get("type") == "text":
                parts.append(block.get("text", ""))
            elif block.get("type") == "image_url":
                parts.append("[IMAGE]")
        return " ".join(parts)
    return str(content)
