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

import logging
import os

import uvicorn
from dotenv import load_dotenv

from src.api import app
from src.logging_config import setup_logging

# --- Logger Configuration ---
setup_logging()
_logger = logging.getLogger(__name__)

# Load .env file, required when locally developing
load_dotenv()

# --- Configuration from Environment Variables ---
_HOST = os.getenv("HOST", "0.0.0.0")
_PORT = int(os.getenv("PORT", 11434))

if __name__ == "__main__":
    # noinspection HttpUrlsUsage
    _logger.info(f"Starting Gemini proxy on http://{_HOST}:{_PORT}")
    uvicorn.run(app, host=_HOST, port=_PORT)
