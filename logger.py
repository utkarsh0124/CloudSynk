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

        file_handler = RotatingFileHandler(self.__get_log_file_name(), maxBytes=500*1024, backupCount=5)
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)

        self.logger.addHandler(console_handler)
        self.logger.addHandler(file_handler)

    def __get_log_file_name(self):
        current_time = datetime.now().strftime("%y%m%d_%H%M%S")
        log_directory = "log"
        os.makedirs(log_directory, exist_ok=True)
        return os.path.join(log_directory, f'boot_{current_time}.log')