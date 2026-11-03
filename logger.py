"""
ExamApp Dataset Generator Logger
Provides structured, thread-safe console and file logging with immediate auto-flush and fsync.
"""

import logging
import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_LOG_FILE = os.path.join(BASE_DIR, "dataset_generator.log")

class FlushingFileHandler(logging.FileHandler):
    """
    FileHandler that automatically flushes on every emit and syncs to disk (fsync),
    ensuring real-time log updates in open editors (VS Code, Notepad, tail, Powershell)
    without OS disk buffering delay.
    """
    def emit(self, record):
        super().emit(record)
        try:
            self.flush()
            if self.stream and hasattr(self.stream, "fileno"):
                os.fsync(self.stream.fileno())
        except Exception:
            pass

def setup_logger(name: str = "ExamApp", log_file: str = DEFAULT_LOG_FILE) -> logging.Logger:
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)

    # Console Handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_format = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S"
    )
    console_handler.setFormatter(console_format)
    logger.addHandler(console_handler)

    # File Handler with Immediate Auto-Flush & Disk Sync
    try:
        file_handler = FlushingFileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)
        file_format = logging.Formatter(
            "%(asctime)s [%(levelname)s] (%(filename)s:%(lineno)d): %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        file_handler.setFormatter(file_format)
        logger.addHandler(file_handler)
    except Exception:
        pass

    return logger

logger = setup_logger()


