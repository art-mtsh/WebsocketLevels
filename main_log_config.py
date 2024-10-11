import logging
import colorlog
import os

def setup_logger():
    # Create a custom logger
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)  # Global logger level

    # Check if the logger already has handlers to prevent adding duplicates
    if not logger.hasHandlers():
        path_to_log = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'main.log')

        # Create handlers
        console_handler = logging.StreamHandler()
        file_handler = logging.FileHandler(path_to_log, encoding='utf-8')

        # Set levels for handlers
        console_handler.setLevel(logging.DEBUG)
        file_handler.setLevel(logging.DEBUG)

        # Create formatters and add them to handlers
        color_formatter = colorlog.ColoredFormatter(
            '%(log_color)s%(asctime)s %(levelname)s %(filename)s:%(name)s:%(lineno)d\n'
            '-------------------------------------------------------|%(log_color)s %(message)s',
            log_colors={
                'DEBUG':    'cyan',
                'INFO':     'green',
                'WARNING':  'yellow',
                'ERROR':    'red',
                'CRITICAL': 'bold_red',
            },
            datefmt='%H:%M:%S'  # Format for time only
        )

        file_formatter = logging.Formatter(
            '%(asctime)s %(levelname)s %(filename)s:%(name)s:%(lineno)d\n'
            '-------------------------------------------------------| %(message)s',
            datefmt='%H:%M:%S'  # Format for time only
        )

        console_handler.setFormatter(color_formatter)
        file_handler.setFormatter(file_formatter)

        # Add handlers to the logger
        logger.addHandler(console_handler)
        logger.addHandler(file_handler)

        # Suppress debug logs from all libraries
        for lib_logger in logging.Logger.manager.loggerDict.values():
            if isinstance(lib_logger, logging.Logger):
                lib_logger.setLevel(logging.WARNING)

        # CRITICAL(50)
        # ERROR(40)
        # WARNING(30)
        # INFO(20)
        # DEBUG(10)
        # NOTSET(0)

        # Specifically suppress debug logs from libraries
        logging.getLogger('matplotlib').setLevel(logging.WARNING)
        logging.getLogger('urllib3').setLevel(logging.WARNING)
        logging.getLogger('PIL').setLevel(logging.WARNING)
        logging.getLogger('websockets').setLevel(logging.WARNING)
