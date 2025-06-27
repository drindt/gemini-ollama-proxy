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

import asyncio
import hashlib
import json
import logging
import os
import sys
import time
from datetime import datetime, timezone

import google.genai as genai
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, PlainTextResponse, StreamingResponse
from google.genai import types
from google.genai.types import GenerateContentConfig

from src.models import (
    ChatCompletionRequest,
    OllamaModelCard,
    OllamaModelDetails,
    OllamaModelList,
)

# --- Logger Configuration ---
_logger = logging.getLogger(__name__)

# --- FastAPI App Configuration ---
app = FastAPI(
    title="Gemini Ollama Proxy",
    description="A lightweight proxy that lets you use Google's Gemini API through"
    "an Ollama-compatible interface.",
)

# --- Gemini Client Configuration ---
_GENAI_API_KEY = os.getenv("GENAI_API_KEY")
if _GENAI_API_KEY:
    _logger.info(
        f"Google AI API Key loaded successfully (ending with ...{_GENAI_API_KEY[-7:]})"
    )
else:
    _logger.error(
        "Google AI API Key not found. Please set GENAI_API_KEY environment variable."
    )
    sys.exit(1)

try:
    _client = genai.Client(api_key=_GENAI_API_KEY)
except Exception as e:
    _logger.error(f"Error initializing Gemini client: {e}", exc_info=True)


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
    _logger.info(f"--> Incoming request: {request.method} {request.url.path}")

    # --- Log Request Body ---
    request_body = await request.body()
    if request_body:
        try:
            _logger.debug(
                f"    Request body: {json.dumps(json.loads(request_body), indent=2)}"
            )
        except json.JSONDecodeError:
            _logger.debug(
                f"    Request body (not JSON): {request_body.decode(errors='ignore')}"
            )
        except Exception as e:
            _logger.debug(f"    Could not log request body: {e}")

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
    _logger.info(
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

    _logger.debug(f"    {response_body_log_message}")
    return response


@app.get("/api/tags", response_model=OllamaModelList)
async def list_ollama_models():
    """
    Retrieves the available models from the Google Gemini API,
    transforms them into the Ollama-compatible format, and returns them.
    """
    if not _client:
        raise HTTPException(status_code=500, detail="Gemini client not initialized.")

    _logger.info(
        "Request to /api/tags received. Fetching the actual Gemini model list..."
    )
    try:
        available_models = await asyncio.to_thread(_client.models.list)
        ollama_formatted_models = []

        for model in available_models:
            if "generateContent" in model.supported_actions:
                base_model_name = model.name.replace("models/", "")
                fake_digest = hashlib.sha256(base_model_name.encode()).hexdigest()

                card = OllamaModelCard(
                    details=OllamaModelDetails(families=[model.display_name]),
                    digest=fake_digest,
                    display_name=model.display_name,
                    model=base_model_name,
                    name=base_model_name,
                )
                ollama_formatted_models.append(card.model_dump())

        response_data = {"models": ollama_formatted_models}
        _logger.info(
            f"Sending {len(ollama_formatted_models)} transformed models to the client."
        )

        response = JSONResponse(content=response_data)
        _logger.debug(f"Response data:\n{json.dumps(response_data, indent=2)}")

        return response

    except Exception as e2:
        _logger.error(
            f"Error fetching or transforming Gemini models: {e2}",
            exc_info=True,
        )
        return JSONResponse(content={"models": []}, status_code=500)


@app.post("/api/chat")
@app.post("/v1/chat/completions")
async def chat_completions(raw_request: Request):
    """
    Handles chat completion requests, converting from an Ollama-like format to Gemini's API.
    This version manually cleans the request body to prevent validation errors.
    """
    if not _client:
        raise HTTPException(status_code=500, detail="Gemini client not initialized.")

    # --- Manually parse and clean the request body to handle client inconsistencies ---
    try:
        json_body = await raw_request.json()

        # Fix for clients sending messages without a 'content' field.
        if "messages" in json_body and isinstance(json_body["messages"], list):
            for message in json_body["messages"]:
                if (
                    isinstance(message, dict)
                    and "role" in message
                    and "content" not in message
                ):
                    message["content"] = ""
                    _logger.debug("Patched a message missing the 'content' field.")

        # Now, validate the cleaned body with the Pydantic model.
        request = ChatCompletionRequest.model_validate(json_body)

    except Exception as e:
        _logger.error(
            f"Error processing or validating request body: {e}", exc_info=True
        )
        raise HTTPException(status_code=400, detail=f"Invalid request body: {e}")

    # --- Convert Ollama messages to Gemini's format ---
    system_instruction = None
    messages_for_gemini = request.messages

    # Heuristic to detect and promote a system prompt from clients (like JetBrains)
    # that send it as the first user message.
    if messages_for_gemini:
        first_message = messages_for_gemini[0]
        is_system_prompt = first_message.role == "system"
        is_like_system_prompt = (
            first_message.role == "user" and "you must" in first_message.content.lower()
        )

        if is_system_prompt or is_like_system_prompt:
            _logger.info(
                f"Promoting message from role '{first_message.role}' to system instruction."
            )
            system_instruction = first_message.content
            messages_for_gemini = messages_for_gemini[1:]

    api_contents = []
    for msg in messages_for_gemini:
        role = "model" if msg.role == "assistant" else msg.role
        api_contents.append(
            types.Content(role=role, parts=[types.Part(text=msg.content)])
        )

    # --- Dynamically create generation config from request ---
    generation_config = GenerateContentConfig(
        seed=request.seed,
        stop_sequences=request.stop,
        system_instruction=system_instruction,
        temperature=request.temperature,
        top_p=request.top_p,
    )

    model_name_for_api = f"models/{request.model}"

    if request.stream:

        async def run_sync_stream_in_thread():
            loop = asyncio.get_running_loop()
            queue = asyncio.Queue()
            try:

                def generator_thread():
                    try:
                        response_iterator = _client.models.generate_content_stream(
                            config=generation_config,
                            contents=api_contents,
                            model=model_name_for_api,
                        )
                        for generated_value in response_iterator:
                            loop.call_soon_threadsafe(queue.put_nowait, generated_value)

                    except Exception as generator_error:
                        loop.call_soon_threadsafe(queue.put_nowait, generator_error)

                    finally:
                        loop.call_soon_threadsafe(queue.put_nowait, None)

                await loop.run_in_executor(None, generator_thread)

                while True:
                    item = await queue.get()
                    if item is None:
                        break
                    if isinstance(item, Exception):
                        raise item
                    yield item
            except Exception as stream_error:
                _logger.error(f"Error in stream wrapper: {stream_error}", exc_info=True)

        async def stream_generator():
            try:
                async for response_content in run_sync_stream_in_thread():
                    response_chunk = {
                        "created_at": datetime.now(timezone.utc).isoformat(),
                        "done": False,
                        "message": {
                            "role": "assistant",
                            "content": response_content.text,
                        },
                        "model": request.model,
                    }
                    yield f"{json.dumps(response_chunk)}\n"

                final_chunk = {
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "done": True,
                    "eval_count": 0,
                    "eval_duration": 1,
                    "load_duration": 1,
                    "message": {
                        "content": "",
                        "role": "assistant",
                    },
                    "model": request.model,
                    "prompt_eval_count": 0,
                    "total_duration": 1,
                }
                yield f"{json.dumps(final_chunk)}\n"

            except Exception as stream_error:
                _logger.error(f"Error during streaming: {stream_error}", exc_info=True)

        return StreamingResponse(stream_generator(), media_type="application/x-ndjson")
    else:
        try:
            response = await asyncio.to_thread(
                _client.models.generate_content,
                config=generation_config,
                contents=api_contents,
                model=model_name_for_api,
            )
            response_json = {
                "choices": [
                    {
                        "finish_reason": "stop",
                        "index": 0,
                        "message": {
                            "content": response.text,
                            "role": "assistant",
                        },
                    }
                ],
                "created": int(time.time()),
                "id": "chatcmpl-default",
                "model": request.model,
                "object": "chat.completion",
                "usage": {
                    "completion_tokens": response.usage_metadata.candidates_token_count,
                    "prompt_tokens": response.usage_metadata.prompt_token_count,
                    "total_tokens": response.usage_metadata.total_token_count,
                },
            }
            _logger.debug(
                f"Sending non-stream response: {json.dumps(response_json, indent=2)}"
            )
            return JSONResponse(content=response_json)
        except Exception as non_stream_error:
            _logger.error(
                f"Error in non-stream request: {non_stream_error}", exc_info=True
            )
            raise HTTPException(status_code=500, detail=str(non_stream_error))


@app.get("/")
def read_root():
    """
    Root endpoint of the API.

    Returns:
        A simple message indicating the API is running.
    """
    _logger.debug("Root request received.")
    return PlainTextResponse("Ollama is running.")


@app.get("/health")
async def health():
    """
    Health check endpoint.

    Returns:
        A status message indicating the service is healthy.
    """
    _logger.debug("Health check request received.")
    return JSONResponse(content={"status": "healthy"})
