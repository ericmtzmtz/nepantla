import time
import traceback

from fastapi import Request
from fastapi.responses import JSONResponse


async def error_handler_middleware(request: Request, call_next):
    try:
        start = time.time()
        response = await call_next(request)
        elapsed = time.time() - start
        response.headers["X-Process-Time-Ms"] = str(int(elapsed * 1000))
        return response
    except Exception as exc:
        resp = JSONResponse(
            status_code=500,
            content={
                "error": {
                    "type": type(exc).__name__,
                    "message": str(exc),
                    "detail": traceback.format_exc() if request.app.debug else None,
                }
            },
        )
        resp.headers["Access-Control-Allow-Origin"] = "*"
        resp.headers["Access-Control-Allow-Methods"] = "*"
        resp.headers["Access-Control-Allow-Headers"] = "*"
        return resp
