import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime
#import inspect
import sys

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
        formatter = logging.Formatter('[{levelname}]::{asctime}::[{source_module}]::{message}', style='{')

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
        return f'boot_{current_time}.log'

    def __log(self, level, message, func_name):
        self.logger.log(level, message, extra={'source_module': func_name})

    def info(self, message):
        func_name = sys._getframe(1).f_code.co_name
        # caller_frame = inspect.stack()[1]
        # func_name = caller_frame.function
        self.__log(logging.INFO, message, func_name)

    def debug(self, message):
        func_name = sys._getframe(1).f_code.co_name
        # caller_frame = inspect.stack()[1]
        # func_name = caller_frame.function
        self.__log(logging.DEBUG, message, func_name)

    def error(self, message):
        func_name = sys._getframe(1).f_code.co_name
        # caller_frame = inspect.stack()[1]
        # func_name = caller_frame.function
        self.__log(logging.ERROR, message, func_name)

    def warning(self, message):
        func_name = sys._getframe(1).f_code.co_name
        # caller_frame = inspect.stack()[1]
        # func_name = caller_frame.function
        self.__log(logging.WARNING, message, func_name)
