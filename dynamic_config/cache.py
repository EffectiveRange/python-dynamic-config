from types import MappingProxyType
from typing import Any, cast

from argparse import Namespace


class ConfigSnapshot(Namespace):

    def __init__(self, values: dict[str, Any]) -> None:
        object.__setattr__(self, "_values", MappingProxyType(dict(values)))

    def __getattr__(self, name: str) -> Any:
        try:
            return self._values[name]
        except KeyError:
            raise AttributeError(name)

    def __setattr__(self, name: str, value: Any) -> None:
        raise AttributeError("ConfigSnapshot is immutable")

    def __delattr__(self, name: str) -> None:
        raise AttributeError("ConfigSnapshot is immutable")

    def values(self) -> dict[str, Any]:
        return dict(self._values)


class ConfigCache(Namespace):
    def __init__(self, initial: dict[str, Any] | None = None) -> None:
        object.__setattr__(self, "_snapshot", ConfigSnapshot(initial or {}))

    def __getattr__(self, name: str) -> Any:
        return getattr(self._snapshot, name)

    def __setattr__(self, name: str, value: Any) -> None:
        raise AttributeError("ConfigCache is read-only; configuration is updated by the update() method")

    def snapshot(self) -> ConfigSnapshot:
        return cast(ConfigSnapshot, self._snapshot)

    def update(self, values: dict[str, Any]) -> None:
        object.__setattr__(self, "_snapshot", ConfigSnapshot(values))
