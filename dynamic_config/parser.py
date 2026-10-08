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
from io import StringIO
from typing import Any, cast


class ConfigAction(Action):

    def __init__(self, *args: Any, dynamic: bool = False, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.dynamic = dynamic
        self.container: _ArgumentGroup | None = None

    def __call__(
        self,
        parser: ArgumentParser,
        namespace: Namespace,
        values: Any,
        option_string: str | None = None,
    ) -> None:
        setattr(namespace, self.dest, values)


class ConfigContainer(_ActionsContainer):

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.register("type", None, lambda x: x)

    def add_config_argument(
        self, *args: Any, dynamic: bool = False, **kwargs: Any
    ) -> ConfigAction:
        kwargs["action"] = ConfigAction
        kwargs["dynamic"] = dynamic
        return cast(ConfigAction, self.add_argument(*args, **kwargs))

    def add_config_argument_group(
        self, *args: Any, **kwargs: Any
    ) -> "ConfigArgumentGroup":
        group = ConfigArgumentGroup(self, *args, **kwargs)
        self._action_groups.append(group)
        return group


class ConfigArgumentGroup(_ArgumentGroup, ConfigContainer):
    pass


class ConfigArgumentParser(ArgumentParser, ConfigContainer):

    def __init__(
        self, *args: Any, default_section: str = "default", **kwargs: Any
    ) -> None:
        kwargs.__setitem__("argument_default", SUPPRESS)
        kwargs.setdefault("formatter_class", ArgumentDefaultsHelpFormatter)
        ArgumentParser.__init__(self, *args, **kwargs)
        self._default_section = default_section

    def get_defaults(self) -> dict[str, Any]:
        defaults = self._get_defaults(self)

        for group in self._action_groups:
            defaults.update(self._get_defaults(group))

        return defaults

    def dump_defaults(self, print_to_console: bool = False) -> str:
        config = ConfigParser()

        for action in self._actions:
            if isinstance(action, ConfigAction) and action.default not in (
                SUPPRESS,
                None,
            ):
                if action.container and action.container.title:
                    section = action.container.title

                    if section == "options":
                        section = self._default_section

                    if section not in config:
                        config[section] = {}

                    config[section][action.dest] = str(action.default)

        with StringIO() as stream:
            config.write(stream)
            result = stream.getvalue()

        if print_to_console:
            print(result)

        return result

    def parse_config(self, config: dict[str, Any]) -> Namespace:
        args = []

        for action in self._actions:
            if isinstance(action, ConfigAction) and action.dest in config:
                value = config[action.dest]

                if isinstance(action, BooleanOptionalAction):
                    value = str(value).lower()

                    if value in ("true", "yes", "1", "on"):
                        args.append(action.option_strings[0])
                    elif value in ("false", "no", "0", "off"):
                        args.append(action.option_strings[1])
                    else:
                        raise ValueError(f"Invalid boolean value: {value}")
                else:
                    option = action.option_strings[0]
                    args.extend([option, value])

        return self.parse_args(args)

    def _get_defaults(self, container: _ActionsContainer) -> dict[str, Any]:
        default = {}

        for action in container._actions:
            if action.default not in (SUPPRESS, None):
                default[action.dest] = action.default

        return default
