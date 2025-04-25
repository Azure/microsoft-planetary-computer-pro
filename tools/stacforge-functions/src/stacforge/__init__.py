import azure.durable_functions as df  # type: ignore
import azure.functions as func

from stacforge.base_model import BaseActivityInput

blueprint = df.Blueprint(http_auth_level=func.AuthLevel.FUNCTION)

__all__ = [
    "BaseActivityInput",
    "blueprint",
]
