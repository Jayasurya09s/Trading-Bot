from __future__ import annotations

from functools import wraps
from time import sleep
from typing import Any, Callable, Iterable, Tuple, Type

from utils.logger import get_logger


def retry(
    func: Callable | None = None,
    *,
    retries: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: Tuple[Type[BaseException], ...] = (Exception,),
):
    logger = get_logger(__name__)

    def decorator(target: Callable):
        @wraps(target)
        def wrapper(*args: Any, **kwargs: Any):
            current_delay = delay
            last_error: BaseException | None = None

            for attempt in range(1, retries + 1):
                try:
                    return target(*args, **kwargs)
                except exceptions as exc:  # pragma: no cover - retry path is exercised in integration flows
                    last_error = exc
                    logger.warning(
                        "Retry attempt %s/%s for %s failed: %s",
                        attempt,
                        retries,
                        target.__name__,
                        exc,
                    )
                    if attempt == retries:
                        raise
                    sleep(current_delay)
                    current_delay *= backoff

            if last_error:
                raise last_error

        return wrapper

    if func is not None:
        return decorator(func)
    return decorator
import time

def retry(func, retries=3, delay=2):
    def wrapper(*args, **kwargs):
        for i in range(retries):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                if i == retries - 1:
                    raise
                time.sleep(delay)
    return wrapper