"""Operational logging with no provider payloads or HTTP wire logs."""

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from uuid import uuid4


def configure_logging(verbose: bool, log_file: Path | None) -> None:
    logger = logging.getLogger("caniwatch")
    for handler in logger.handlers[:]:
        handler.close()
        logger.removeHandler(handler)
    logger.propagate = False
    logger.setLevel(logging.DEBUG if verbose else logging.INFO)
    formatter = logging.Formatter(
        f"%(asctime)s %(levelname)s run={uuid4().hex[:8]} %(name)s %(message)s"
    )
    if verbose:
        console = logging.StreamHandler()
        console.setFormatter(formatter)
        logger.addHandler(console)
    if log_file:
        handler = RotatingFileHandler(log_file, maxBytes=1_000_000, backupCount=2, encoding="utf-8")
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    if not logger.handlers:
        logger.addHandler(logging.NullHandler())
    # HTTP libraries may include request URLs and untrusted failure messages.
    for name in ("httpx", "httpcore"):
        logging.getLogger(name).setLevel(logging.CRITICAL)
