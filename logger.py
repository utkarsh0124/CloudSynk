import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime
import inspect
import os
import threading
# import sys
class Logger:
    _instance = None
    _lock = threading.Lock()
    
    @classmethod
    def init_logger(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
        return cls._instance
    def __init__(self):
        # Prevent re-initialization if logger already exists
        if hasattr(self, 'logger'):
            return
            
        self.logger = logging.getLogger('cloudsynk')
        self.logger.setLevel(logging.DEBUG)
        
        # Prevent duplicate handlers if logger already has handlers
        if self.logger.handlers:
            return
            
        formatter = logging.Formatter('%(asctime)s::[%(levelname)s]::[%(module)s.py]::[%(funcName)s::%(lineno)d]::%(message)s')
        
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.ERROR)
        console_handler.setFormatter(formatter)

        # Use fixed log file name for continuous logging
        file_handler = RotatingFileHandler(self.__get_log_file_name(), maxBytes=10*1024*1024, backupCount=10)
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)

        self.logger.addHandler(console_handler)
        self.logger.addHandler(file_handler)

    def __get_log_file_name(self):
        log_directory = "log"
        os.makedirs(log_directory, exist_ok=True)
        # Use fixed filename for continuous logging across restarts
        return os.path.join(log_directory, 'cloudsynk.log')