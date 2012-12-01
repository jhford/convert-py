import logging

def setup_logging(loggername, volume=1, console=True, filename=None):
    logger = logging.getLogger(loggername)
    levels = [logging.DEBUG, logging.INFO, logging.WARNING, logging.ERROR, logging.CRITICAL]
    if volume >= len(levels):
        volume = len(levels) - 1
    elif volume < 0:
        volume = 0
    logger.setLevel(levels[len(levels)-volume-1])
    if console:
        console_handler = logging.StreamHandler()
        console_formatter = logging.Formatter('%(levelname)s: %(message)s')
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)
    if filename:
        file_handler = logging.FileHandler(filename)
        file_formatter = logging.Formatter('%(asctime) - %(levelname)s: %(message)s')
        file_handler.addFormatter(file_formatter)
        logger.addHandler(file_handler)
    return logger
