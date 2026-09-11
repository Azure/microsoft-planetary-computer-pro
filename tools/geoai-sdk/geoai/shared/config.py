"""
geoai.shared.config

Configuration management for GeoAI SDK.
"""

import os


class Config:
    """
    Configuration container for GeoAI SDK.

    Loads configuration from environment variables with sensible defaults.
    """

    def __init__(self):
        self.max_workers = 4
        self.timeout = 3600
        self.retry_attempts = 3

    @classmethod
    def from_env(cls):
        """
        Load configuration from environment variables.

        Environment variables:
            GEOAI_MAX_WORKERS: Maximum concurrent workers (default: 4)
            GEOAI_TIMEOUT: Request timeout in seconds (default: 3600)
            GEOAI_RETRY_ATTEMPTS: Number of retry attempts (default: 3)

        :return: Config instance with values from environment or defaults
        """
        config = cls()
        config.max_workers = int(os.getenv("GEOAI_MAX_WORKERS", config.max_workers))
        config.timeout = int(os.getenv("GEOAI_TIMEOUT", config.timeout))
        config.retry_attempts = int(os.getenv("GEOAI_RETRY_ATTEMPTS", config.retry_attempts))
        return config
