from re import RegexFlag
from typing import Any, Dict

GeoTemplateGlobals: Dict[str, Any] = {
    "RE_NOFLAG": RegexFlag.NOFLAG,
    "RE_ASCII": RegexFlag.ASCII,  # assume ascii "locale"
    "RE_IGNORECASE": RegexFlag.IGNORECASE,  # ignore case
    "RE_LOCALE": RegexFlag.LOCALE,  # assume current 8-bit locale
    "RE_UNICODE": RegexFlag.UNICODE,  # assume unicode "locale"
    "RE_MULTILINE": RegexFlag.MULTILINE,  # make anchors look for newline
    "RE_DOTALL": RegexFlag.DOTALL,  # make dot match newline
    "RE_VERBOSE": RegexFlag.VERBOSE,  # ignore whitespace and comments
}
"""
A dictionary of global variables that can be accessed in a GeoTemplate.
"""
