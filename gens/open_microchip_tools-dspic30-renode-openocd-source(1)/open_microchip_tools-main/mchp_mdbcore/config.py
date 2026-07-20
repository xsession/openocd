from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Iterable, List, Optional, Protocol, Union


class ConfigEvent(Enum):
    CONFIG_CHANGED = "CONFIG_CHANGED"


class ConfigObserver(Protocol):
    def update(self, event: ConfigEvent) -> None:
        ...


ObserverLike = Union[ConfigObserver, Callable[[ConfigEvent], None]]


class Config(Protocol):
    def addObserver(self, observer: ObserverLike) -> None:  # Java name
        ...

    def removeObserver(self, observer: ObserverLike) -> None:  # Java name
        ...

    def get(self) -> int:  # Java name
        ...

    def getAddress(self) -> int:  # Java name
        ...

    def getConfigFieldDesc(self) -> Any:  # Java name
        ...


@dataclass
class ObservableConfig:
    """Minimal config value container with observer support.

    Pythonic API:
      - `value`, `address`, `config_field_desc`
      - `add_observer()`, `remove_observer()`

    Java shims:
      - `get()`, `getAddress()`, `getConfigFieldDesc()`
      - `addObserver()`, `removeObserver()`
    """

    address: int
    value: int = 0
    config_field_desc: Any = None
    _observers: List[ObserverLike] = field(default_factory=list, init=False, repr=False)

    def add_observer(self, observer: ObserverLike) -> None:
        if observer not in self._observers:
            self._observers.append(observer)

    def remove_observer(self, observer: ObserverLike) -> None:
        self._observers = [o for o in self._observers if o is not observer]

    def notify(self, event: ConfigEvent = ConfigEvent.CONFIG_CHANGED) -> None:
        for observer in list(self._observers):
            try:
                if callable(observer):
                    observer(event)
                else:
                    observer.update(event)
            except Exception:
                continue

    def set_value(self, new_value: int) -> None:
        new_value_int = int(new_value)
        if new_value_int == self.value:
            return
        self.value = new_value_int
        self.notify(ConfigEvent.CONFIG_CHANGED)

    # Java method-name shims
    def addObserver(self, observer: ObserverLike) -> None:
        self.add_observer(observer)

    def removeObserver(self, observer: ObserverLike) -> None:
        self.remove_observer(observer)

    def get(self) -> int:
        return int(self.value)

    def getAddress(self) -> int:
        return int(self.address)

    def getConfigFieldDesc(self) -> Any:
        return self.config_field_desc


# Optional Java-ish nested-type compatibility.
class _JavaLikeConfigObserver:
    class ConfigEvent(Enum):
        CONFIG_CHANGED = "CONFIG_CHANGED"

    def update(self, event: "_JavaLikeConfigObserver.ConfigEvent") -> None:  # pragma: no cover
        raise NotImplementedError


class JavaLikeConfig:
    ConfigObserver = _JavaLikeConfigObserver
