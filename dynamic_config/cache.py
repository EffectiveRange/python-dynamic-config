# SPDX-FileCopyrightText: 2024 Ferenc Nandor Janky <ferenj@effective-range.com>
# SPDX-FileCopyrightText: 2024 Attila Gombos <attila.gombos@effective-range.com>
# SPDX-License-Identifier: MIT

from abc import ABC, abstractmethod
from types import MappingProxyType
from typing import Any, cast

from argparse import Namespace


class Snapshot(ABC):

    @abstractmethod
    def values(self) -> dict[str, Any]: ...


class Cache(ABC):

    @abstractmethod
    def get(self) -> Namespace: ...

    @abstractmethod
    def snapshot(self) -> Namespace: ...

    @abstractmethod
    def update(self, values: dict[str, Any]) -> None: ...

    @abstractmethod
    def clear(self) -> None: ...


class ConfigSnapshot(Snapshot, Namespace):

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

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Namespace):
            return NotImplemented
        return bool(self._values == vars(other))

    def __contains__(self, key: object) -> bool:
        return key in self._values

    def values(self) -> dict[str, Any]:
        return dict(self._values)


class ConfigCache(Cache, Namespace):
    def __init__(self, initial: dict[str, Any] | None = None) -> None:
        object.__setattr__(self, "_snapshot", ConfigSnapshot(initial or {}))

    def __getattr__(self, name: str) -> Any:
        return getattr(self._snapshot, name)

    def __setattr__(self, name: str, value: Any) -> None:
        raise AttributeError("ConfigCache is read-only; configuration is updated by the update() method")

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Namespace):
            return NotImplemented
        return bool(self._snapshot._values == vars(other))

    def __contains__(self, key: object) -> bool:
        return key in self._snapshot._values

    def get(self) -> Namespace:
        return self

    def snapshot(self) -> Namespace:
        return cast(Namespace, self._snapshot)

    def update(self, values: dict[str, Any]) -> None:
        object.__setattr__(self, "_snapshot", ConfigSnapshot(values))

    def clear(self) -> None:
        object.__setattr__(self, "_snapshot", ConfigSnapshot({}))
