#!/usr/bin/env python3

from argparse import BooleanOptionalAction
from dynamic_config import ConfigArgumentParser


def get_parser() -> ConfigArgumentParser:
    parser = ConfigArgumentParser()

    parser.add_argument("--config-dir", required=True)  # Can only be set as command line argument
    parser.add_config_argument("--port", type=int, default=8080)  # Static after initialization
    parser.add_config_argument("--enabled", action=BooleanOptionalAction, default=True, dynamic=True)

    group = parser.add_config_group("security")
    group.add_config_argument("--passphrase")
    group.add_config_argument("--private-key", default="./keys/private.key")
    group.add_config_argument("--public-key", default="./keys/public.key")

    group = parser.add_config_group("database")
    group.add_config_argument("--db-host", default="127.0.0.1", dynamic=True)
    group.add_config_argument("--db-port", type=int, default=12345, dynamic=True)

    return parser


if __name__ == "__main__":
    parser = get_parser()
    parser.default_config(print_to_console=True)
