import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime
import inspect
import os
# import sys


class Logger:
    _instance = None

    @classmethod
    def init_logger(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)
        formatter = logging.Formatter('%(asctime)s::[%(levelname)s]::[%(module)s.py]::[%(funcName)s::%(lineno)d]::%(message)s')

        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.ERROR)
        console_handler.setFormatter(formatter)

        # Try to create a file handler in repo `log/`; if that's not writable, fall back
        # to a per-user directory under /tmp so file logging still works without root.
        file_path = None
        try:
            file_path = self.__get_log_file_name()
            file_handler = RotatingFileHandler(file_path, maxBytes=500*1024, backupCount=5)
            file_handler.setLevel(logging.DEBUG)
            file_handler.setFormatter(formatter)
            self.logger.addHandler(file_handler)
        except PermissionError:
            try:
                # Use a temp directory per user
                user = os.environ.get('USER') or os.getlogin()
            except Exception:
                user = 'unknown'
            tmp_dir = os.path.join('/tmp', f'StorageApp-logs-{user}')
            try:
                os.makedirs(tmp_dir, exist_ok=True)
                tmp_log = os.path.join(tmp_dir, os.path.basename(self.__get_log_file_name()))
                file_handler = RotatingFileHandler(tmp_log, maxBytes=500*1024, backupCount=5)
                file_handler.setLevel(logging.DEBUG)
                file_handler.setFormatter(formatter)
                self.logger.addHandler(file_handler)
                # Inform about alternative log location
                print(f"INFO: log directory not writable; using fallback log at {tmp_log}")
            except Exception:
                # Final fallback: console only
                console_handler.setLevel(logging.WARNING)
                console_handler.setFormatter(formatter)
                self.logger.addHandler(console_handler)
                print("WARNING: unable to create log file; falling back to console logging")
                return

        self.logger.addHandler(console_handler)

    def __get_log_file_name(self):
        current_time = datetime.now().strftime("%y%m%d_%H%M%S")
        log_directory = "log"
        try:
            os.makedirs(log_directory, exist_ok=True)
            return os.path.join(log_directory, f'boot_{current_time}.log')
        except PermissionError:
            # Let caller handle fallback
            return os.path.join(log_directory, f'boot_{current_time}.log')
