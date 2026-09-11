"""
geoai.public.constraint

Base Constraint class - Defines spatial/temporal constraints for models.
"""


class BaseConstraint:
    """
    BaseConstraint - Base class for all constraint types.

    All model constraints inherit from this to ensure consistent interface.
    """

    def __init__(self):
        pass

    def validate(self):
        """
        Validate constraint parameters.

        :raises ValueError: If constraint parameters are invalid
        """
        raise NotImplementedError("Subclasses must implement validate()")
