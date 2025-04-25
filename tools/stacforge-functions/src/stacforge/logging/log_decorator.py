import logging
from functools import wraps
from typing import Any, Callable, Coroutine

from stacforge.logging.logging import LOGGER_NAME
from stacforge.utils import Timer

_logger = logging.getLogger(LOGGER_NAME)


def log(func: Callable) -> Callable:
    """Log the function name, arguments, return value, and time taken to execute."""

    @wraps(func)
    def wrapper(*args, **kwargs) -> Any:
        args_repr = [repr(a) for a in args]
        kwargs_repr = [f"{k}={v!r}" for k, v in kwargs.items()]
        formatted_args = ", ".join(args_repr + kwargs_repr)
        formatted_args = "no arguments" if not formatted_args else formatted_args
        extra = {
            "funcName_override": func.__name__,
            "module_override": func.__module__.split(".")[-1],
        }
        _logger.debug(
            f"Calling '{func.__name__}' with {formatted_args}",
            extra=extra,
        )
        try:
            with Timer() as timer:
                return_value = func(*args, **kwargs)
        except Exception as e:
            _logger.error(f"Error calling {func.__name__}: {e}")
            raise
        if isinstance(return_value, Coroutine):
            _logger.debug(
                f"'{func.__name__}' invoked asynchronously",
                extra=extra,
            )
        else:
            _logger.debug(
                f"'{func.__name__}' took {timer() * 1_000:.6f} ms and returned {return_value!r}",  # noqa: E501
                extra=extra,
            )
        return return_value

    return wrapper
