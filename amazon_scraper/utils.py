import functools
import logging
import random
import time

from amazon_scraper import config


def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)
    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    try:
        file_handler = logging.FileHandler("scraper.log")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    except OSError:
        pass

    return logger


log = get_logger("amazon_scraper")


def polite_delay(min_seconds: float = None, max_seconds: float = None) -> None:
    lo = config.MIN_DELAY if min_seconds is None else min_seconds
    hi = config.MAX_DELAY if max_seconds is None else max_seconds
    time.sleep(random.uniform(lo, hi))


def retry_with_backoff(max_retries: int = None, backoff_factor: float = None):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            retries = config.MAX_RETRIES if max_retries is None else max_retries
            factor = config.BACKOFF_FACTOR if backoff_factor is None else backoff_factor

            last_exception = None
            for attempt in range(1, retries + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as exc:
                    last_exception = exc
                    if attempt == retries:
                        break
                    wait = (factor ** (attempt - 1)) + random.uniform(0, 1)
                    log.warning(
                        "Attempt %d/%d failed for %s (%s). Retrying in %.1fs",
                        attempt, retries, func.__name__, exc, wait,
                    )
                    time.sleep(wait)
            log.error("All %d attempts failed for %s: %s", retries, func.__name__, last_exception)
            raise last_exception

        return wrapper
    return decorator
