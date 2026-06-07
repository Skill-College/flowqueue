"""FlowQueue Python SDK — sync client for the FlowQueue message platform."""

from .client import FlowQueueClient
from .consumer import FlowQueueConsumer
from .errors import ApiError, FlowQueueError
from .models import Delivery

__version__ = "0.1.0"

__all__ = [
    "FlowQueueClient",
    "FlowQueueConsumer",
    "Delivery",
    "FlowQueueError",
    "ApiError",
    "__version__",
]
