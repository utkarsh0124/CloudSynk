from logger import Logger
import logging

Logger.init_logger()

logger = Logger._instance.logger

severity = {
    'DEBUG': logging.DEBUG,
    'INFO': logging.INFO,
    'ERROR': logging.ERROR,
    'WARNING': logging.WARNING
}
