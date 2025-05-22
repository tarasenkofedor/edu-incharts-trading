import logging
import sys

DEFAULT_LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(module)s:%(funcName)s:%(lineno)d - %(message)s"


def setup_logging(level=logging.INFO, log_format=None):
    """Configures basic logging for the service."""
    if log_format is None:
        log_format = DEFAULT_LOG_FORMAT

    logging.basicConfig(
        level=level,
        format=log_format,
        handlers=[
            logging.StreamHandler(sys.stdout)  # Log to stdout
        ]
    )
    # You can also add file handlers here if needed
    # For example:
    # file_handler = logging.FileHandler("data_ingestion_service.log")
    # file_handler.setFormatter(logging.Formatter(log_format))
    # logging.getLogger().addHandler(file_handler)

    logging.info("Logging configured.")


if __name__ == "__main__":
    setup_logging(logging.DEBUG)
    logging.debug("This is a debug message.")
    logging.info("This is an info message.")
    logging.warning("This is a warning message.")
    logging.error("This is an error message.") 