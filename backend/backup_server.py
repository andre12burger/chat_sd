#!/usr/bin/env python3
"""
Backup Server - Entry Point.

Monitor ativo-passivo com heartbeat (código real em backup/monitor.py).
"""

import logging
import sys

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [%(threadName)s] - %(message)s'
)
logger = logging.getLogger(__name__)

from backup import BackupServer


if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("Backup Server (modo passivo)")
    logger.info("Monitorando servidor principal em 127.0.0.1:5000")
    logger.info("=" * 60)

    try:
        backup = BackupServer()
        backup.start()
    except KeyboardInterrupt:
        logger.info("Backup server parado.")
        sys.exit(0)
