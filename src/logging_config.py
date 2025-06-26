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
import sys


def setup_logging():
    """
    Configures the root logging for the application.
    Logs to standard output (stdout) by default, which is good for containers.
    """
    log_level = os.getenv("LOG_LEVEL", "info").upper()

    # logging.basicConfig configures the root logger.
    # Other modules can then simply use `logging.getLogger(__name__)`.
    logging.basicConfig(
        datefmt="%Y-%m-%d %H:%M:%S",
        format="%(asctime)s [%(levelname)s] %(message)s",
        level=log_level,
        stream=sys.stdout,
    )

    # Logger for the configuration module itself to confirm the setup.
    logger = logging.getLogger(__name__)
    logger.info(f"Logging configured with level: {log_level}")
