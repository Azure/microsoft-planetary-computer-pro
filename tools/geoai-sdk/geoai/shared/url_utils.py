"""
geoai.shared.url_utils

URL validation utilities for secure domain checking.
"""

from typing import List, Optional
from urllib.parse import urlparse


def is_trusted_domain(url: str, trusted_domains: Optional[List[str]] = None) -> bool:
    """
    Securely validate if a URL belongs to a trusted domain.

    Uses proper URL parsing to prevent bypass attacks via:
    - Substring matching (trusted.com in evil.com/trusted.com)
    - Userinfo injection (user@trusted.com@evil.com)
    - Subdomain tricks (trusted.com.evil.com)

    Args:
        url: URL to validate
        trusted_domains: List of trusted domains. Defaults to ['planetarycomputer.microsoft.com']

    Returns:
        True if URL is from a trusted domain with HTTPS scheme and no credentials

    Security requirements:
        - HTTPS scheme only
        - No embedded credentials (user:pass@host)
        - Exact hostname match or approved subdomain
        - Proper URL parsing (not substring matching)
    """
    if trusted_domains is None:
        trusted_domains = ["planetarycomputer.microsoft.com"]

    try:
        parsed = urlparse(url)

        # Reject non-HTTPS schemes
        if parsed.scheme != "https":
            return False

        # Reject URLs with embedded credentials (user:pass@host)
        if parsed.username is not None or parsed.password is not None:
            return False

        # Get the hostname (None if invalid URL structure)
        hostname = parsed.hostname
        if not hostname:
            return False

        # Normalize to lowercase for comparison
        hostname = hostname.lower()

        # Check against trusted domains
        for trusted in trusted_domains:
            trusted = trusted.lower()

            # Exact match
            if hostname == trusted:
                return True

            # Subdomain match (e.g., api.planetarycomputer.microsoft.com)
            if hostname.endswith(f".{trusted}"):
                return True

        return False

    except Exception:
        # Invalid URL format or parsing error - reject
        return False
