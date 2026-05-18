#!/usr/bin/env python3
"""
Web Gateway - Entry Point.

Flask/SocketIO web gateway (código real em gateway/app.py).
"""

import logging
import sys

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [%(name)s] - %(message)s'
)
logging.getLogger('werkzeug').setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

from gateway import run_app


if __name__ == "__main__":
    try:
        run_app()
    except KeyboardInterrupt:
        logger.info("Web Gateway parado.")
        sys.exit(0)
