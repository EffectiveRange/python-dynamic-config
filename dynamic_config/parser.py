# SPDX-FileCopyrightText: 2024 Ferenc Nandor Janky <ferenj@effective-range.com>
# SPDX-FileCopyrightText: 2024 Attila Gombos <attila.gombos@effective-range.com>
# SPDX-License-Identifier: MIT

from abc import ABC, abstractmethod
from argparse import (
    SUPPRESS,
    _ActionsContainer,
    _ArgumentGroup,
    Action,
    ArgumentDefaultsHelpFormatter,
    ArgumentParser,
    BooleanOptionalAction,
    Namespace,
)
from configparser import ConfigParser
from dataclasses import dataclass
from io import StringIO
from typing import Any


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
        default = kwargs.pop("default", None)
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
        arguments = dict(self._config_args)

        for group in self.get_config_groups():
            arguments.update(group.get_config_arguments())

        return arguments

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


class ConfigArgumentParser(Parser, ArgumentParser, ConfigContainer):

    def __init__(self, *args: Any, default_section: str = "default", **kwargs: Any) -> None:
        kwargs.__setitem__("argument_default", SUPPRESS)
        kwargs.setdefault("formatter_class", ArgumentDefaultsHelpFormatter)
        ArgumentParser.__init__(self, *args, **kwargs)
        ConfigContainer.__init__(self, default_section, *args, **kwargs)

    def get_defaults(self) -> dict[str, Any]:
        defaults = self._get_defaults(self)

        for group in self._action_groups:
            defaults.update(self._get_defaults(group))

        return defaults

    def default_config(self, print_to_console: bool = False) -> str:
        config = ConfigParser()

        config = self._get_config_defaults(config, self)

        for group in self.get_config_groups():
            config = self._get_config_defaults(config, group)

        with StringIO() as stream:
            config.write(stream)
            result = stream.getvalue()

        if print_to_console:
            print(result)

        return result

    def parse_config(self, config: dict[str, Any]) -> Namespace:
        args = []
        config_arguments = list(self.get_config_arguments().values())

        for group in self.get_config_groups():
            config_arguments.extend(group.get_config_arguments().values())

        for argument in config_arguments:
            if argument.action.dest in config:
                value = config[argument.action.dest]

                if isinstance(argument.action, BooleanOptionalAction):
                    value = str(value).lower()

                    if value in ("true", "yes", "1", "on"):
                        args.append(argument.action.option_strings[0])
                    else:
                        args.append(argument.action.option_strings[1])
                else:
                    option = argument.action.option_strings[0]
                    args.extend([option, value])

        return self.parse_args(args)

    def _get_defaults(self, container: _ActionsContainer) -> dict[str, Any]:
        defaults = {}

        for action in container._actions:
            if action.dest in self._config_args:
                defaults[action.dest] = self._config_args[action.dest].default
            elif action.default not in (SUPPRESS, None):
                defaults[action.dest] = action.default

        return defaults

    def _get_config_defaults(self, config: ConfigParser, container: ConfigContainer) -> ConfigParser:
        for argument in container._config_args.values():
            if argument.default not in (SUPPRESS, None):
                section = container.title

                if section not in config:
                    config[section] = {}

                config[section][argument.action.dest] = str(argument.default)

        return config
