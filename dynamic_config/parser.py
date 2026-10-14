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
    dynamic: bool
    action: Action
    container: "ConfigContainer"


class ConfigContainer(_ActionsContainer):

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        if not hasattr(self, "_actions"):
            super().__init__(*args, **kwargs)
        self.register("type", None, lambda x: x)
        self.title = args[0] if args else kwargs.get("title", "")
        self._arguments: dict[str, ConfigArgument] = {}

    def add_config_argument(self, *args: Any, dynamic: bool = False, **kwargs: Any) -> ConfigArgument:
        action = self.add_argument(*args, **kwargs)
        argument = ConfigArgument(action=action, dynamic=dynamic, container=self)
        self._arguments[action.dest] = argument
        return argument

    def add_config_group(self, *args: Any, **kwargs: Any) -> "ConfigArgumentGroup":
        group = ConfigArgumentGroup(self, *args, **kwargs)
        self._action_groups.append(group)
        return group

    def get_config_groups(self) -> list["ConfigArgumentGroup"]:
        return [group for group in self._action_groups if isinstance(group, ConfigArgumentGroup)]

    def get_config_arguments(self) -> dict[str, ConfigArgument]:
        return self._arguments

    def get_dynamic_arguments(self) -> dict[str, ConfigArgument]:
        return {dest: action for dest, action in self.get_config_arguments().items() if action.dynamic}


class ConfigArgumentGroup(_ArgumentGroup, ConfigContainer):
    def __init__(self, container: ConfigContainer, *args: Any, **kwargs: Any) -> None:
        update = kwargs.setdefault
        update("conflict_handler", container.conflict_handler)
        update("prefix_chars", container.prefix_chars)
        update("argument_default", container.argument_default)
        _ArgumentGroup.__init__(self, container, *args, **kwargs)
        ConfigContainer.__init__(self, *args, **kwargs)


class ConfigArgumentParser(ArgumentParser, ConfigContainer):

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
                    elif value in ("false", "no", "0", "off"):
                        args.append(argument.action.option_strings[1])
                    else:
                        raise ValueError(f"Invalid boolean value: {value}")
                else:
                    option = argument.action.option_strings[0]
                    args.extend([option, value])

        return self.parse_args(args)

    def _get_defaults(self, container: _ActionsContainer) -> dict[str, Any]:
        default = {}

        for action in container._actions:
            if action.default not in (SUPPRESS, None):
                default[action.dest] = action.default

        return default

    def _get_config_defaults(self, config: ConfigParser, container: ConfigContainer) -> ConfigParser:
        for argument in container._arguments.values():
            if argument.action.default not in (SUPPRESS, None):
                section = container.title

                if section not in config:
                    config[section] = {}

                config[section][argument.action.dest] = str(argument.action.default)

        return config
