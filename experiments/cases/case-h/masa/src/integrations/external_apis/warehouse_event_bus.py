class WarehouseEventBus:
    def __init__(self):
        self._events: list[dict[str, str | int | None]] = []

    def publish(self, event_type: str, payload: dict[str, str | int | None]) -> None:
        event = {"event_type": event_type}
        event.update(payload)
        self._events.append(event)

    def list_events(self) -> list[dict[str, str | int | None]]:
        return list(self._events)
