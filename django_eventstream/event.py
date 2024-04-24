from dataclasses import dataclass
from typing import Optional

# Object class replaced with dataclass for type safety


@dataclass
class Event:
    channel: str
    type: str
    data: dict
    id: Optional[int] = None
