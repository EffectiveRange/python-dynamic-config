# SPDX-FileCopyrightText: 2024 Ferenc Nandor Janky <ferenj@effective-range.com>
# SPDX-FileCopyrightText: 2024 Attila Gombos <attila.gombos@effective-range.com>
# SPDX-License-Identifier: MIT

from abc import ABC, abstractmethod
from argparse import (
    SUPPRESS,
    _ActionsContainer,
    _ArgumentGroup,
    _StoreAction,
    _StoreFalseAction,
    _StoreTrueAction,
    Action,
    ArgumentError,
    ArgumentDefaultsHelpFormatter,
    ArgumentParser,
    BooleanOptionalAction,
    Namespace,
)
from configparser import ConfigParser
from copy import copy, deepcopy
from dataclasses import dataclass
from io import StringIO
import shlex
from typing import Any, NoReturn


class ConfigError(ValueError):
    """A configuration value cannot be parsed."""


class ConfigValueParser(ArgumentParser):

    def error(self, message: str) -> NoReturn:
        raise ConfigError(message)


@dataclass
class ConfigArgument:
    action: Action
    dynamic: bool
    default: Any
    container: "ConfigContainer"


class Container(ABC):

    @abstractmethod
    def add_config_argument(self, *args: Any, dynamic: bool = False, **kwargs: Any) -> ConfigArgument: ...

    @abstractmethod
    def add_config_group(self, *args: Any, **kwargs: Any) -> "ConfigArgumentGroup": ...

    @abstractmethod
    def get_config_groups(self) -> list["ConfigArgumentGroup"]: ...

    @abstractmethod
    def get_config_arguments(self) -> dict[str, ConfigArgument]: ...

    @abstractmethod
    def get_dynamic_arguments(self) -> dict[str, ConfigArgument]: ...


class Parser(Container):

    @abstractmethod
    def get_defaults(self) -> dict[str, Any]: ...

    @abstractmethod
    def default_config(self, print_to_console: bool = False) -> str: ...

    @abstractmethod
    def parse_config(self, config: dict[str, Any]) -> Namespace: ...


class ConfigContainer(Container, _ActionsContainer):

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        if not hasattr(self, "_actions"):
            super().__init__(*args, **kwargs)
        self.register("type", None, lambda x: x)
        self.title = args[0] if args else kwargs.get("title", "")
        self._config_args: dict[str, ConfigArgument] = {}

    def add_config_argument(self, *args: Any, dynamic: bool = False, **kwargs: Any) -> ConfigArgument:
        if not args or any(not isinstance(arg, str) or not arg or arg[0] not in self.prefix_chars for arg in args):
            raise ValueError("Configuration arguments must be named options, not positional arguments")

        action_type = kwargs.get("action", "store")
        action_class = self._registry_get("action", action_type, action_type)
        if action_class not in (_StoreAction, _StoreTrueAction, _StoreFalseAction, BooleanOptionalAction):
            raise ValueError("Configuration arguments support store, store_true, store_false and BooleanOptionalAction")

        nargs = kwargs.get("nargs")
        if nargs not in (None, "?", "+", "*") and not (isinstance(nargs, int) and nargs > 0):
            raise ValueError("Unsupported nargs for configuration argument")

        default = kwargs.pop("default", None)
        kwargs["default"] = SUPPRESS

        action = self.add_argument(*args, **kwargs)
        action.required = False

        argument = ConfigArgument(action, dynamic, default, self)
        self._config_args[action.dest] = argument

        return argument

    def add_config_group(self, *args: Any, **kwargs: Any) -> "ConfigArgumentGroup":
        group = ConfigArgumentGroup(self, *args, **kwargs)
        self._action_groups.append(group)
        return group

    def get_config_groups(self) -> list["ConfigArgumentGroup"]:
        return [group for group in self._action_groups if isinstance(group, ConfigArgumentGroup)]

    def get_config_arguments(self) -> dict[str, ConfigArgument]:
        return dict(self._config_args)

    def get_dynamic_arguments(self) -> dict[str, ConfigArgument]:
        return {dest: argument for dest, argument in self.get_config_arguments().items() if argument.dynamic}


class ConfigArgumentGroup(_ArgumentGroup, ConfigContainer):
    def __init__(self, container: ConfigContainer, *args: Any, **kwargs: Any) -> None:
        update = kwargs.setdefault
        update("conflict_handler", container.conflict_handler)
        update("prefix_chars", container.prefix_chars)
        update("argument_default", container.argument_default)
        _ArgumentGroup.__init__(self, container, *args, **kwargs)
        ConfigContainer.__init__(self, *args, **kwargs)
        self._config_args = container._config_args


class ConfigArgumentParser(Parser, ArgumentParser, ConfigContainer):

    def __init__(self, *args: Any, default_section: str = "default", **kwargs: Any) -> None:
        kwargs.__setitem__("argument_default", SUPPRESS)
        kwargs.setdefault("formatter_class", ArgumentDefaultsHelpFormatter)
        ArgumentParser.__init__(self, *args, **kwargs)
        ConfigContainer.__init__(self, default_section, *args, **kwargs)

    def get_defaults(self) -> dict[str, Any]:
        defaults = {}

        for action in self._actions:
            if action.dest in self._config_args:
                if (default := self._config_args[action.dest].default) not in (SUPPRESS, None):
                    defaults[action.dest] = default
            elif action.default not in (SUPPRESS, None):
                defaults[action.dest] = action.default

        return defaults

    def default_config(self, print_to_console: bool = False) -> str:
        config = ConfigParser()

        for argument in self._config_args.values():
            if argument.default not in (SUPPRESS, None):
                section = argument.container.title

                if section not in config:
                    config[section] = {}

                value = argument.default
                config[section][argument.action.dest] = (
                    shlex.join(str(item) for item in value) if isinstance(value, (list, tuple)) else str(value)
                )

        with StringIO() as stream:
            config.write(stream)
            result = stream.getvalue()

        if print_to_console:
            print(result, end="")

        return result

    def parse_config(self, config: dict[str, Any]) -> Namespace:
        result = self._regular_defaults()

        for argument in self.get_config_arguments().values():
            action = argument.action
            if action.dest in config:
                setattr(result, action.dest, self._parse_value(action, config[action.dest]))

        return result

    def _regular_defaults(self) -> Namespace:
        result = Namespace()

        for action in self._actions:
            if action.dest not in self._config_args and action.default != SUPPRESS:
                default = deepcopy(action.default)

                if isinstance(default, str):
                    try:
                        default = self._get_value(action, default)
                    except ArgumentError as error:
                        raise ConfigError(str(error)) from error

                setattr(result, action.dest, default)

        return result

    def _parse_value(self, action: Action, value: Any) -> Any:
        if isinstance(action, (BooleanOptionalAction, _StoreTrueAction, _StoreFalseAction)):
            normalized = str(value).lower()

            if normalized not in ("true", "yes", "1", "on", "false", "no", "0", "off"):
                raise ConfigError(f"{action.dest}: invalid boolean value: {value!r}")

            return normalized in ("true", "yes", "1", "on")

        value_parser = ConfigValueParser(add_help=False, prefix_chars=self.prefix_chars)
        value_action = copy(action)
        value_action.type = self._registry_get("type", action.type, action.type)

        value_parser._add_action(value_action)

        option = action.option_strings[0]

        if action.nargs in (None, "?"):
            args = [f"{option}={value}"]
        else:
            try:
                values = shlex.split(value) if isinstance(value, str) else [str(item) for item in value]
            except (TypeError, ValueError) as error:
                raise ConfigError(f"{action.dest}: invalid sequence: {value!r}") from error

            args = [option, *values]

        parsed = value_parser.parse_args(args)

        return getattr(parsed, action.dest)
