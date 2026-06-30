# ruff: noqa: E501

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from server.core.database import get_db
from server.core.dependencies import verify_api_key
from server.modules.analytics.services import AnalyticsService
from server.modules.providers.registry import ProviderRegistry
from server.modules.providers.schemas import (
    AudioTranscriptionOptions,
    ChatMessage,
    CompletionOptions,
    TextToSpeechOptions,
)
from server.modules.router.schemas import PoolType
from server.modules.router.services import RouterService

router = APIRouter()


@router.post("/v1/chat/completions")
async def chat_completion(
    request: Request,
    db: AsyncSession = Depends(get_db),
    api_key: str = Depends(verify_api_key),
):
    body = await request.json()
    messages_data = body.get("messages", [])
    model = body.get("model", "auto")
    stream = body.get("stream", False)

    # Parse messages
    messages = [ChatMessage(role=m["role"], content=m["content"]) for m in messages_data]

    # Classify pool (vision check + tools check)
    tools = body.get("tools")
    pool = PoolType.CHAT
    if tools:
        pool = PoolType.CHAT_TOOLS
    elif model in ("auto", "nepantla-model") or not model:
        for msg in messages:
            if isinstance(msg.content, list):
                for block in msg.content:
                    if block.get("type") == "image_url":
                        pool = PoolType.VISION
                        break

    # Build options
    options = CompletionOptions(
        temperature=body.get("temperature"),
        max_tokens=body.get("max_tokens"),
        top_p=body.get("top_p"),
        stream=stream,
        tools=tools,
        tool_choice=body.get("tool_choice"),
        parallel_tool_calls=body.get("parallel_tool_calls"),
    )

    # If model specified directly (not auto), find provider
    if model not in ("auto", "nepantla-model"):
        from sqlalchemy import select

        from server.modules.providers.models import ProviderCatalog
        result = await db.execute(
            select(ProviderCatalog).where(ProviderCatalog.model_id == model).where(ProviderCatalog.enabled)
        )
        model_row = result.scalar_one_or_none()
        if not model_row:
            await AnalyticsService.record_request(db, "chat", "unknown", model, None, "error", error="model_not_found")
            raise HTTPException(status_code=404, detail=f"Model '{model}' not found")
        provider = ProviderRegistry.get(model_row.platform)
        if not provider:
            await AnalyticsService.record_request(db, "chat", model_row.platform, model, None, "error", error="provider_not_found")
            raise HTTPException(status_code=404, detail=f"Provider '{model_row.platform}' not found")

        # Get API key
        from server.modules.keys.models import ApiKey
        key_result = await db.execute(
            select(ApiKey).where(ApiKey.platform == model_row.platform).where(ApiKey.enabled).limit(1)
        )
        api_key_obj = key_result.scalar_one_or_none()
        if not api_key_obj:
            await AnalyticsService.record_request(db, "chat", model_row.platform, model, None, "error", error="no_active_key")
            raise HTTPException(status_code=503, detail=f"No active API key for {model_row.platform}")

        from server.lib.crypto import decrypt
        decrypted_key = decrypt(api_key_obj.encrypted_key, api_key_obj.iv, api_key_obj.auth_tag)

        if stream:
            from fastapi.responses import StreamingResponse
            async def stream_gen():
                async for chunk in provider.stream_chat_completion(decrypted_key, messages, model, options):
                    yield f"data: {chunk.model_dump_json()}\n\n"
                yield "data: [DONE]\n\n"
            return StreamingResponse(stream_gen(), media_type="text/event-stream")
        else:
            resp = await provider.chat_completion(decrypted_key, messages, model, options)
            usage = resp.usage or {}
            await RouterService.record_request(
                db, model_row.platform, model, api_key_obj.id,
                usage.get("prompt_tokens", 0), usage.get("completion_tokens", 0),
            )
            await AnalyticsService.record_request(
                db, "chat", model_row.platform, model, api_key_obj.id,
                "success", usage.get("prompt_tokens", 0), usage.get("completion_tokens", 0),
            )
            return resp.model_dump()
    else:
        # Auto-routing with fallback chain — try each candidate until one works
        from server.lib.crypto import decrypt

        last_error = "No available provider"
        while True:
            messages_hash = str(hash(str(messages))) if messages else ""
            route = await RouterService.select_fallback(db, pool, messages_hash)
            if not route:
                await AnalyticsService.record_request(
                    db, "chat", "unknown", pool, None, "error", 0, 0, error="no_candidate",
                )
                raise HTTPException(status_code=429, detail=last_error)

            provider = route["provider"]
            api_key_obj = route["api_key"]
            decrypted_key = decrypt(api_key_obj.encrypted_key, api_key_obj.iv, api_key_obj.auth_tag)

            try:
                if stream:
                    from fastapi.responses import StreamingResponse
                    async def stream_gen():
                        async for chunk in provider.stream_chat_completion(decrypted_key, messages, route["model_id"], options):
                            yield f"data: {chunk.model_dump_json()}\n\n"
                        yield "data: [DONE]\n\n"
                    return StreamingResponse(stream_gen(), media_type="text/event-stream")
                else:
                    resp = await provider.chat_completion(decrypted_key, messages, route["model_id"], options)
                    usage = resp.usage or {}
                    await RouterService.record_request(
                        db, route["platform"], route["model_id"], route["api_key"].id,
                        usage.get("prompt_tokens", 0), usage.get("completion_tokens", 0),
                    )
                    await AnalyticsService.record_request(
                        db, "chat", route["platform"], route["model_id"], route["api_key"].id,
                        "success", usage.get("prompt_tokens", 0), usage.get("completion_tokens", 0),
                    )
                    return resp.model_dump()
            except Exception as e:
                last_error = str(e)
                # Clear sticky session so retry picks a different provider
                if messages_hash:
                    RouterService._sticky_sessions.pop(f"{pool}:{messages_hash}", None)
                await RouterService.set_cooldown(db, route["platform"], route["model_id"], route["api_key"].id, penalty=1)
                await AnalyticsService.record_request(
                    db, "chat", route["platform"], route["model_id"], route["api_key"].id,
                    "error", error=last_error,
                )
                await db.flush()
                continue


@router.post("/v1/images/generations")
async def image_generation(
    request: Request,
    db: AsyncSession = Depends(get_db),
    api_key: str = Depends(verify_api_key),
):
    """Generate image(s) from a text prompt."""
    body = await request.json()
    prompt = body.get("prompt", "")
    if not prompt:
        raise HTTPException(status_code=400, detail="prompt is required")
    model = body.get("model", "auto")

    # Build options
    from server.modules.providers.schemas import ImageGenOptions
    options = ImageGenOptions(
        model=model if model not in ("auto", "nepantla-model") else None,
        n=body.get("n"),
        size=body.get("size"),
        quality=body.get("quality"),
        style=body.get("style"),
        response_format=body.get("response_format", "url"),
    )

    # If model specified directly
    if model not in ("auto", "nepantla-model"):
        from sqlalchemy import select

        from server.lib.crypto import decrypt
        from server.modules.providers.models import ProviderCatalog

        result = await db.execute(
            select(ProviderCatalog).where(ProviderCatalog.model_id == model).where(ProviderCatalog.enabled)
        )
        model_row = result.scalar_one_or_none()
        if not model_row:
            await AnalyticsService.record_request(db, "image_gen", "unknown", model, None, "error", error="model_not_found")
            raise HTTPException(status_code=404, detail=f"Model '{model}' not found")

        provider = ProviderRegistry.get(model_row.platform)
        if not provider:
            await AnalyticsService.record_request(db, "image_gen", model_row.platform, model, None, "error", error="provider_not_found")
            raise HTTPException(status_code=404, detail=f"Provider '{model_row.platform}' not found")

        from server.modules.keys.models import ApiKey
        key_result = await db.execute(
            select(ApiKey).where(ApiKey.platform == model_row.platform).where(ApiKey.enabled).limit(1)
        )
        api_key_obj = key_result.scalar_one_or_none()
        if not api_key_obj:
            await AnalyticsService.record_request(db, "image_gen", model_row.platform, model, None, "error", error="no_active_key")
            raise HTTPException(status_code=503, detail=f"No active API key for {model_row.platform}")

        decrypted_key = decrypt(api_key_obj.encrypted_key, api_key_obj.iv, api_key_obj.auth_tag)

        try:
            resp = await provider.image_generation(decrypted_key, prompt, options)
        except RuntimeError as e:
            await AnalyticsService.record_request(db, "image_gen", model_row.platform, model, api_key_obj.id, "error", error=str(e))
            raise HTTPException(status_code=502, detail=str(e))
        except Exception as e:
            await AnalyticsService.record_request(db, "image_gen", model_row.platform, model, api_key_obj.id, "error", error=f"provider_error: {str(e)}")
            raise HTTPException(status_code=502, detail=f"Provider error: {str(e)}")

        # Record analytics
        await RouterService.record_request(
            db, model_row.platform, model, api_key_obj.id,
            input_tokens=len(prompt) // 4, output_tokens=1000,  # ponytail: fixed estimate per image
        )
        await AnalyticsService.record_request(db, "image_gen", model_row.platform, model, api_key_obj.id, "success", len(prompt) // 4, 1000)
        await db.commit()

        return resp.model_dump()

    # Auto-routing via image_gen pool with fallback chain
    from server.lib.crypto import decrypt

    last_error = "No available provider for image generation"
    while True:
        route = await RouterService.select_fallback(db, PoolType.IMAGE_GEN)
        if not route:
            await AnalyticsService.record_request(db, "image_gen", "unknown", "nepantla-model", None, "error", error="no_candidate")
            raise HTTPException(status_code=429, detail=last_error)

        provider = route["provider"]
        api_key_obj = route["api_key"]
        decrypted_key = decrypt(api_key_obj.encrypted_key, api_key_obj.iv, api_key_obj.auth_tag)

        try:
            resp = await provider.image_generation(decrypted_key, prompt, options)
        except Exception as e:
            last_error = str(e)
            await RouterService.set_cooldown(db, route["platform"], route["model_id"], route["api_key"].id, penalty=1)
            await AnalyticsService.record_request(db, "image_gen", route["platform"], route["model_id"], route["api_key"].id, "error", error=last_error)
            await db.flush()
            continue

        await RouterService.record_request(
            db, route["platform"], route["model_id"], route["api_key"].id,
            input_tokens=len(prompt) // 4, output_tokens=1000,
        )
        await AnalyticsService.record_request(db, "image_gen", route["platform"], route["model_id"], route["api_key"].id, "success", len(prompt) // 4, 1000)
        await db.commit()
        return resp.model_dump()


@router.post("/v1/audio/transcriptions")
async def audio_transcription(
    request: Request,
    db: AsyncSession = Depends(get_db),
    api_key: str = Depends(verify_api_key),
):
    """Transcribe audio file to text."""
    from fastapi import UploadFile
    from fastapi.responses import JSONResponse

    body = await request.form()
    audio_file: UploadFile | None = body.get("file")
    if not audio_file:
        raise HTTPException(status_code=400, detail="file is required")

    file_bytes = await audio_file.read()
    model_id = body.get("model", "auto")
    language = body.get("language")

    opts = AudioTranscriptionOptions(language=language)

    if model_id not in ("auto", "nepantla-model"):
        from sqlalchemy import select

        from server.lib.crypto import decrypt
        from server.modules.keys.models import ApiKey
        from server.modules.providers.models import ProviderCatalog

        result = await db.execute(
            select(ProviderCatalog).where(ProviderCatalog.model_id == model_id).where(ProviderCatalog.enabled)
        )
        model_row = result.scalar_one_or_none()
        if not model_row:
            await AnalyticsService.record_request(db, "audio", "unknown", model_id, None, "error", error="model_not_found")
            raise HTTPException(status_code=404, detail=f"Model '{model_id}' not found")

        provider = ProviderRegistry.get(model_row.platform)
        if not provider:
            await AnalyticsService.record_request(db, "audio", model_row.platform, model_id, None, "error", error="provider_not_found")
            raise HTTPException(status_code=404, detail=f"Provider '{model_row.platform}' not found")

        key_result = await db.execute(
            select(ApiKey).where(ApiKey.platform == model_row.platform).where(ApiKey.enabled).limit(1)
        )
        api_key_obj = key_result.scalar_one_or_none()
        if not api_key_obj:
            await AnalyticsService.record_request(db, "audio", model_row.platform, model_id, None, "error", error="no_active_key")
            raise HTTPException(status_code=503, detail=f"No active API key for {model_row.platform}")

        decrypted_key = decrypt(api_key_obj.encrypted_key, api_key_obj.iv, api_key_obj.auth_tag)
        resp = await provider.audio_transcription(decrypted_key, file_bytes, audio_file.filename or "audio.wav", opts)

        await RouterService.record_request(
            db, model_row.platform, model_id, api_key_obj.id,
            input_tokens=len(file_bytes), output_tokens=0,
        )
        await AnalyticsService.record_request(db, "audio", model_row.platform, model_id, api_key_obj.id, "success", len(file_bytes), 0)
        await db.commit()
        return JSONResponse(resp.model_dump())

    # Auto-routing with fallback chain
    from server.lib.crypto import decrypt

    last_error = "No available provider for audio transcription"
    while True:
        route = await RouterService.select_fallback(db, PoolType.AUDIO)
        if not route:
            await AnalyticsService.record_request(db, "audio", "unknown", "nepantla-model", None, "error", error="no_candidate")
            raise HTTPException(status_code=429, detail=last_error)

        provider = route["provider"]
        api_key_obj = route["api_key"]
        decrypted_key = decrypt(api_key_obj.encrypted_key, api_key_obj.iv, api_key_obj.auth_tag)

        try:
            resp = await provider.audio_transcription(decrypted_key, file_bytes, audio_file.filename or "audio.wav", opts)
        except Exception as e:
            last_error = str(e)
            await RouterService.set_cooldown(db, route["platform"], route["model_id"], route["api_key"].id, penalty=1)
            await AnalyticsService.record_request(db, "audio", route["platform"], route["model_id"], route["api_key"].id, "error", error=last_error)
            await db.flush()
            continue

        await RouterService.record_request(
            db, route["platform"], route["model_id"], route["api_key"].id,
            input_tokens=len(file_bytes), output_tokens=0,
        )
        await AnalyticsService.record_request(db, "audio", route["platform"], route["model_id"], route["api_key"].id, "success", len(file_bytes), 0)
        await db.commit()
        return JSONResponse(resp.model_dump())


@router.post("/v1/audio/speech")
async def text_to_speech(
    request: Request,
    db: AsyncSession = Depends(get_db),
    api_key: str = Depends(verify_api_key),
):
    """Convert text to speech audio."""
    from fastapi.responses import StreamingResponse

    body = await request.json()
    input_text = body.get("input", "")
    if not input_text:
        raise HTTPException(status_code=400, detail="input is required")
    model_id = body.get("model", "auto")

    opts = TextToSpeechOptions(
        voice=body.get("voice"),
        speed=body.get("speed"),
        response_format=body.get("response_format"),
    )

    if model_id not in ("auto", "nepantla-model"):
        from sqlalchemy import select

        from server.lib.crypto import decrypt
        from server.modules.keys.models import ApiKey
        from server.modules.providers.models import ProviderCatalog

        result = await db.execute(
            select(ProviderCatalog).where(ProviderCatalog.model_id == model_id).where(ProviderCatalog.enabled)
        )
        model_row = result.scalar_one_or_none()
        if not model_row:
            await AnalyticsService.record_request(db, "tts", "unknown", model_id, None, "error", error="model_not_found")
            raise HTTPException(status_code=404, detail=f"Model '{model_id}' not found")

        provider = ProviderRegistry.get(model_row.platform)
        if not provider:
            await AnalyticsService.record_request(db, "tts", model_row.platform, model_id, None, "error", error="provider_not_found")
            raise HTTPException(status_code=404, detail=f"Provider '{model_row.platform}' not found")

        key_result = await db.execute(
            select(ApiKey).where(ApiKey.platform == model_row.platform).where(ApiKey.enabled).limit(1)
        )
        api_key_obj = key_result.scalar_one_or_none()
        if not api_key_obj:
            await AnalyticsService.record_request(db, "tts", model_row.platform, model_id, None, "error", error="no_active_key")
            raise HTTPException(status_code=503, detail=f"No active API key for {model_row.platform}")

        decrypted_key = decrypt(api_key_obj.encrypted_key, api_key_obj.iv, api_key_obj.auth_tag)

        await RouterService.record_request(db, model_row.platform, model_id, api_key_obj.id, input_tokens=len(input_text) // 4, output_tokens=0)
        await AnalyticsService.record_request(db, "tts", model_row.platform, model_id, api_key_obj.id, "success", len(input_text) // 4, 0)

        async def audio_stream():
            async for chunk in provider.text_to_speech(decrypted_key, input_text, opts):
                yield chunk

        return StreamingResponse(audio_stream(), media_type="audio/wav")

    # Auto-routing with fallback chain
    from server.lib.crypto import decrypt

    last_error = "No available provider for text-to-speech"
    while True:
        route = await RouterService.select_fallback(db, PoolType.AUDIO)
        if not route:
            await AnalyticsService.record_request(db, "tts", "unknown", "nepantla-model", None, "error", error="no_candidate")
            raise HTTPException(status_code=429, detail=last_error)

        provider = route["provider"]
        api_key_obj = route["api_key"]
        decrypted_key = decrypt(api_key_obj.encrypted_key, api_key_obj.iv, api_key_obj.auth_tag)

        try:
            await RouterService.record_request(db, route["platform"], route["model_id"], route["api_key"].id, input_tokens=len(input_text) // 4, output_tokens=0)
            await AnalyticsService.record_request(db, "tts", route["platform"], route["model_id"], route["api_key"].id, "success", len(input_text) // 4, 0)
            async def audio_stream():
                async for chunk in provider.text_to_speech(decrypted_key, input_text, opts):
                    yield chunk
            return StreamingResponse(audio_stream(), media_type="audio/wav")
        except Exception as e:
            last_error = str(e)
            await RouterService.set_cooldown(db, route["platform"], route["model_id"], route["api_key"].id, penalty=1)
            await AnalyticsService.record_request(db, "tts", route["platform"], route["model_id"], route["api_key"].id, "error", error=last_error)
            await db.flush()
            continue
