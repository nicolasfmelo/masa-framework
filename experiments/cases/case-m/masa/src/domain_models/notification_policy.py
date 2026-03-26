from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class NotificationPolicy:
    channel: Literal["email", "slack"]
    remind_before_minutes: int
    send_on_assignment: bool
