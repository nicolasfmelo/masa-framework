from dataclasses import dataclass

VALID_CHANNELS = {"email", "slack"}


@dataclass(frozen=True)
class NotificationPolicy:
    channel: str
    remind_before_minutes: int
    send_on_assignment: bool

    def __post_init__(self) -> None:
        if self.channel not in VALID_CHANNELS:
            raise ValueError(f"Invalid notification channel: {self.channel}")
        if self.remind_before_minutes <= 0:
            raise ValueError("remind_before_minutes must be positive.")
