# SPDX-FileCopyrightText: 2024 Ferenc Nandor Janky <ferenj@effective-range.com>
# SPDX-FileCopyrightText: 2024 Attila Gombos <attila.gombos@effective-range.com>
# SPDX-License-Identifier: MIT

from abc import ABC, abstractmethod
from copy import deepcopy
from types import MappingProxyType
from typing import Any, cast

from argparse import Namespace

from context_logger import get_logger


class Snapshot(ABC):

    @abstractmethod
    def values(self) -> dict[str, Any]: ...


class Cache(ABC):

    @abstractmethod
    def get(self) -> Namespace: ...

    @abstractmethod
    def snapshot(self) -> Namespace: ...

    @abstractmethod
    def update(self, values: dict[str, Any]) -> "Cache": ...

    @abstractmethod
    def replace(self, values: dict[str, Any]) -> "Cache": ...

    @abstractmethod
    def clear(self) -> "Cache": ...


class ConfigSnapshot(Snapshot, Namespace):

    def __init__(self, values: dict[str, Any]) -> None:
        object.__setattr__(self, "_values", MappingProxyType(deepcopy(values)))

    def __getattr__(self, name: str) -> Any:
        try:
            return deepcopy(self._values[name])
        except KeyError:
            raise AttributeError(name)

    def __setattr__(self, name: str, value: Any) -> None:
        raise AttributeError("ConfigSnapshot is immutable")

    def __delattr__(self, name: str) -> None:
        raise AttributeError("ConfigSnapshot is immutable")

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Namespace):
            return NotImplemented
        values = other._values if isinstance(other, ConfigSnapshot) else vars(other)
        return bool(self._values == values)

    def __contains__(self, key: object) -> bool:
        return key in self._values

    def values(self) -> dict[str, Any]:
        return deepcopy(dict(self._values))


class ConfigCache(Cache, Namespace):
    SNAPSHOT_ATTR = "__snapshot"
    LOG_ATTR = "__log"

    def __init__(self, initial: dict[str, Any] | None = None) -> None:
        object.__setattr__(self, self.SNAPSHOT_ATTR, ConfigSnapshot(initial or {}))
        object.__setattr__(self, self.LOG_ATTR, get_logger(type(self).__name__))

    def __getattr__(self, name: str) -> Any:
        return getattr(self._get_snapshot(), name)

    def __setattr__(self, name: str, value: Any) -> None:
        raise AttributeError("ConfigCache is read-only")

    def __delattr__(self, name: str) -> None:
        raise AttributeError("ConfigCache is read-only")

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Namespace):
            return NotImplemented
        if isinstance(other, ConfigCache):
            other = other._get_snapshot()
        return self._get_snapshot() == other

    def __contains__(self, key: object) -> bool:
        return key in self._get_snapshot()._values

    def get(self) -> Namespace:
        return self

    def snapshot(self) -> Namespace:
        return cast(Namespace, getattr(self, self.SNAPSHOT_ATTR))

    def update(self, values: dict[str, Any]) -> "Cache":
        self._log().debug("Updating cache", values=values)
        return self._set_snapshot(self._get_snapshot()._values | values)

    def replace(self, values: dict[str, Any]) -> "Cache":
        self._log().debug("Replacing cache", values=values)
        return self._set_snapshot(values)

    def clear(self) -> "Cache":
        self._log().debug("Clearing cache")
        return self._set_snapshot({})

    def _set_snapshot(self, values: dict[str, Any]) -> "Cache":
        object.__setattr__(self, self.SNAPSHOT_ATTR, ConfigSnapshot(values))
        return self

    def _get_snapshot(self) -> ConfigSnapshot:
        return cast(ConfigSnapshot, getattr(self, self.SNAPSHOT_ATTR))

    def _log(self) -> Any:
        return getattr(self, self.LOG_ATTR)
