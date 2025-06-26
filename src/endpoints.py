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
import time
from datetime import datetime
from datetime import timezone

import google.genai as genai
from fastapi import HTTPException
from fastapi.responses import JSONResponse, StreamingResponse, PlainTextResponse
from google.genai import types
from google.genai.types import GenerateContentConfig

from src.main import GENAI_API_KEY
from src.middleware import app
from src.models import (
    OllamaModelList,
    OllamaModelCard,
    OllamaModelDetails,
    ChatCompletionRequest,
)

# --- Logger Configuration ---
logger = logging.getLogger(__name__)

# --- Gemini Client Configuration ---
try:
    client = genai.Client(api_key=GENAI_API_KEY)
except Exception as e:
    logger.error(f"Error initializing Gemini client: {e}", exc_info=True)


@app.get("/api/tags", response_model=OllamaModelList)
async def list_ollama_models():
    """
    Retrieves the available models from the Google Gemini API,
    transforms them into the Ollama-compatible format, and returns them.
    """
    if not client:
        raise HTTPException(status_code=500, detail="Gemini client not initialized.")

    logger.info(
        "Request to /api/tags received. Fetching the actual Gemini model list..."
    )
    try:
        available_models = await asyncio.to_thread(client.models.list)
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
        logger.info(
            f"Sending {len(ollama_formatted_models)} transformed models to the client."
        )

        response = JSONResponse(content=response_data)
        logger.debug(f"Response data:\n{json.dumps(response_data, indent=2)}")

        return response

    except Exception as e2:
        logger.error(
            f"Error fetching or transforming Gemini models: {e2}",
            exc_info=True,
        )
        return JSONResponse(content={"models": []}, status_code=500)


@app.post("/api/chat")
@app.post("/v1/chat/completions")
async def chat_completions(request: ChatCompletionRequest):
    """
    Handles chat completion requests, converting from an Ollama-like format to Gemini's API.

    Args:
        request: The ChatCompletionRequest containing model, messages, and generation parameters.

    Returns:
        A streaming or non-streaming JSON response containing the model's reply,
        formatted to be compatible with the Ollama API chat completion response.

    Raises:
        HTTPException: If the Gemini client is not initialized or an error occurs during generation.
    """
    if not client:
        raise HTTPException(status_code=500, detail="Gemini client not initialized.")

    # --- Convert Ollama messages to Gemini's format ---
    system_instruction = None
    api_contents = []

    if request.messages and request.messages[0].role == "system":
        system_instruction = request.messages[0].content
        messages_for_gemini = request.messages[1:]
    else:
        messages_for_gemini = request.messages

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
                        response_iterator = client.models.generate_content_stream(
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
                logger.error(f"Error in stream wrapper: {stream_error}", exc_info=True)

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
                logger.error(f"Error during streaming: {stream_error}", exc_info=True)

        return StreamingResponse(stream_generator(), media_type="application/x-ndjson")
    else:
        try:
            response = await asyncio.to_thread(
                client.models.generate_content,
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
            logger.debug(
                f"Sending non-stream response: {json.dumps(response_json, indent=2)}"
            )
            return JSONResponse(content=response_json)
        except Exception as non_stream_error:
            logger.error(
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
    logger.debug("Root request received.")
    return PlainTextResponse("Ollama is running.")


@app.get("/health")
async def health():
    """
    Health check endpoint.

    Returns:
        A status message indicating the service is healthy.
    """
    logger.debug("Health check request received.")
    return JSONResponse(content={"status": "healthy"})
