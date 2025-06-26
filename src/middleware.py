#  MIT License
#
#  Copyright (c) 2025 Daniel Rindt, Viselabs Inc.
#
#  Permission is hereby granted, free of charge, to any person obtaining a copy
#  of this software and associated documentation files (the "Software"), to deal
#  in the Software without restriction, including without limitation the rights
#  to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
#  copies of the Software, and to permit persons to whom the Software is
#  furnished to do so, subject to the following conditions:
#
#  The above copyright notice and this permission notice shall be included in all
#  copies or substantial portions of the Software.
#
#  THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
#  IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#  FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
#  AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
#  LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
#  OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
#  SOFTWARE.

import json
import logging
import time

from fastapi import FastAPI
from fastapi import Request
from fastapi.responses import JSONResponse, StreamingResponse, PlainTextResponse

# --- Logger Configuration ---
logger = logging.getLogger(__name__)

# --- FastAPI App Configuration ---
app = FastAPI(
    title="Gemini Ollama Proxy",
    description="A lightweight proxy that lets you use Google's Gemini API through"
                "an Ollama-compatible interface.",
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    """
    Middleware to log incoming HTTP requests and outgoing responses.

    Logs the request method, path, and optionally the request body (at DEBUG level).
    Logs the response status code, processing time, and optionally the response body (at DEBUG level).

    Args:
        request: The incoming Request object.
        call_next: The next middleware or the endpoint handler in the chain.

    Returns:
        The Response object from the next middleware or endpoint.
    """
    start_time = time.time()
    logger.info(f"--> Incoming request: {request.method} {request.url.path}")

    # --- Log Request Body ---
    request_body = await request.body()
    if request_body:
        try:
            logger.debug(
                f"    Request body: {json.dumps(json.loads(request_body), indent=2)}"
            )
        except json.JSONDecodeError:
            logger.debug(
                f"    Request body (not JSON): {request_body.decode(errors='ignore')}"
            )
        except Exception as e:
            logger.debug(f"    Could not log request body: {e}")

    stream_consumed = False

    async def receive() -> dict:
        nonlocal stream_consumed
        if not stream_consumed:
            stream_consumed = True
            return {
                "body": request_body,
                "type": "http.request",
            }
        return {"type": "http.disconnect"}

    new_request = Request(request.scope, receive)

    # --- Process the request ---
    response = await call_next(new_request)

    # --- Log Response ---
    process_time = (time.time() - start_time) * 1000
    logger.info(
        f"<-- Outgoing response: {response.status_code} (in {process_time:.2f}ms)"
    )

    # --- Log Response Body (at DEBUG level) ---
    try:
        if isinstance(response, (JSONResponse, PlainTextResponse)):
            response_body_bytes = getattr(response, "body", b"")
            if response_body_bytes:
                content_type = response.headers.get("content-type", "")
                decoded_body = response_body_bytes.decode("utf-8", errors="ignore")
                if "application/json" in content_type:
                    try:
                        response_body_log_message = f"Response body (JSON): {json.dumps(json.loads(decoded_body), indent=2)}"
                    except json.JSONDecodeError:
                        response_body_log_message = (
                            f"Response body (JSON, decode error): {decoded_body}"
                        )
                elif "text/plain" in content_type:
                    response_body_log_message = f"Response body (text): {decoded_body}"
                else:
                    response_body_log_message = f"Response body (unhandled content type for logging): {content_type} - {decoded_body[:200]}..."
            else:
                response_body_log_message = "Response body is empty"
        elif isinstance(response, StreamingResponse):
            response_body_log_message = "Response body not logged (StreamingResponse)"
        else:
            response_body_log_message = f"Response body not logged (Unhandled Response Type: {type(response).__name__})"
    except Exception as e:
        response_body_log_message = f"Error logging response body: {e}"

    logger.debug(f"    {response_body_log_message}")
    return response
