from typing import Any, Callable, Protocol


class EngineProtocol(Protocol):
    def run(self, input_data: dict[str, Any]) -> Any: ...


EngineRunFn = Callable[[dict[str, Any]], Any]
