from typing import Callable, Dict

from stacforge.logging import log

GeoTemplateTests: Dict[str, Callable] = {}
"""A dictionary of tests that can be used in a GeoTemplate."""

# Tests can be used to test a variable against a common expression.


def register_test(test: Callable) -> Callable:
    """Add a test to the GeoTemplateTests dictionary"""

    logged_test = log(test)
    GeoTemplateTests[test.__name__] = logged_test
    return logged_test


@register_test
def starts_with(string: str, prefix: str) -> bool:
    """Return `True` if the string starts with the prefix, `False` otherwise."""

    return string.startswith(prefix)


@register_test
def ends_with(string: str, suffix: str) -> bool:
    """Return `True` if the string ends with the suffix, `False` otherwise."""

    return string.endswith(suffix)


@register_test
def contains(string: str, substring: str) -> bool:
    """Return `True` if the string contains the substring, `False` otherwise."""

    return substring in string
