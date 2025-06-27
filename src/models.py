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

from datetime import datetime
from datetime import timezone
from typing import Optional

from pydantic import BaseModel, Field


class OllamaModelDetails(BaseModel):
    """
    Represents the detailed information of an Ollama model.
    """

    families: Optional[list[str]] = Field(
        ["gemini"], description="A list of other associated model families."
    )
    family: Optional[str] = Field(
        "gemini", description="The family of the model (e.g., 'gemini')."
    )
    format: Optional[str] = Field(
        "gguf", description="The format of the model (e.g., 'gguf')."
    )
    parameter_size: Optional[str] = Field(
        "N/A", description="The size of the model parameters (e.g., '7B')."
    )
    quantization_level: Optional[str] = Field(
        "F16", description="The quantization level of the model (e.g., 'Q4_0')."
    )


class OllamaModelCard(BaseModel):
    """
    Represents a single Ollama model card as returned by the API.
    """

    details: OllamaModelDetails = Field(
        description="Detailed information about the model."
    )
    digest: str = Field(description="The digest hash of the model.")
    display_name: str = Field(description="A user-friendly display name for the model.")
    model: str = Field(description="The model ID string.")
    modified_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="The timestamp of the model's last modification.",
    )
    name: str = Field(
        description="The internal name of the model (e.g., 'llama2:latest')."
    )
    size: Optional[int] = Field(
        16106127360, description="The size of the model in bytes."
    )


class OllamaModelList(BaseModel):
    """
    Represents a list of Ollama model cards.
    """

    models: list[OllamaModelCard] = Field(
        description="A list of available Ollama models."
    )


class ChatMessage(BaseModel):
    """
    Represents a single message in a chat context.
    """

    role: str = Field(description="The role of the sender (e.g., 'user', 'assistant').")
    content: str = Field("", description="The content of the message.")


class ChatCompletionRequest(BaseModel):
    """
    Represents a chat completion request, compatible with Ollama API specs.
    """

    model: str = Field(description="The name of the model to use.")
    messages: list[ChatMessage] = Field(description="A list of chat messages.")
    stream: Optional[bool] = Field(
        False, description="Indicates whether the response should be streamed."
    )
    # --- Additions for generation control ---
    temperature: Optional[float] = Field(
        0.5, description="Controls randomness. Lower is more deterministic."
    )
    top_p: Optional[float] = Field(
        1.0, description="Cumulative probability for nucleus sampling."
    )
    seed: Optional[int] = Field(None, description="Seed for reproducible results.")
    stop: Optional[list[str]] = Field(
        None, description="Sequences where the API will stop generating further tokens."
    )
