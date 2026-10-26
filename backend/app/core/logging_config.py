import logging
import os
import sys
from dotenv import load_dotenv
from app.core.request_context import request_id_var

load_dotenv()


class RequestIdFilter(logging.Filter):
    def filter(self, record):
        record.request_id = request_id_var.get()
        return True

def configure_logging():
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()

    handler = logging.StreamHandler(sys.stdout)
    handler.addFilter(RequestIdFilter())

    logging.basicConfig(
        level=getattr(logging, log_level, logging.INFO),
        format="%(asctime)s | %(levelname)s | %(name)s | request_id=%(request_id)s | %(message)s",
        handlers=[handler],
        force=True
    )