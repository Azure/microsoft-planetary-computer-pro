"""
geoai.executors.base

BaseExecutor - Abstract interface for all executors.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict


class BaseExecutor(ABC):
    """
    BaseExecutor - Abstract base class for execution strategies.

    Defines the interface that all executors must implement.
    """

    @abstractmethod
    async def execute(self, workflow_type: str, **kwargs) -> Dict[str, Any]:
        """
        Execute model workflow.

        :param workflow_type: 'aoi_based' or 'weather_forecast'
        :param kwargs: Workflow-specific parameters
        :return: Execution result dictionary
        """
        raise NotImplementedError("Subclasses must implement execute()")
