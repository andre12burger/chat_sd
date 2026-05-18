#!/usr/bin/env python3
"""
Chat Engine - Entry Point.

Servidor TCP puro com threading manual (código real em chat_engine/server.py).
"""

import logging
import sys

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [%(threadName)s] - %(message)s'
)
logger = logging.getLogger(__name__)

from chat_engine import ChatEngine


if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("Chat Engine - Servidor TCP com Threading Manual")
    logger.info("=" * 60)

    try:
        engine = ChatEngine(host="127.0.0.1", port=5000, server_role="primary")
        engine.start()
    except KeyboardInterrupt:
        logger.info("Interrupção do usuário.")
        sys.exit(0)
