#!/usr/bin/env python3

from argparse import BooleanOptionalAction
from logging import INFO
from pathlib import Path
from context_logger import get_logger, setup_logging
from dynamic_config import ConfigArgumentParser, ConfigBuilder, ConfigChange

setup_logging("example")
get_logger("watchdog").setLevel(INFO)


def main() -> None:
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

    args = parser.parse_args()
    config_dir = Path(args.config_dir)

    config = (
        ConfigBuilder(parser)
        .with_defaults()
        .with_file(config_dir / "app.conf")
        .with_directory(config_dir / "app.conf.d")
        .with_environment("APP_")
        .with_arguments()
        .build()
    )

    def on_config_change(file_path: str, changes: dict[str, ConfigChange]) -> None:
        if "db_host" in changes or "db_port" in changes:
            current = config.snapshot()
            db_reconnect(current.db_host, current.db_port)  # Application-provided function

    config.register(on_config_change)

    try:
        config.initialize()

        live = config.get()  # noqa: F841
        snapshot = config.snapshot()  # noqa: F841
        # live.enabled follows future refreshes; snapshot.enabled retains this version.

        run_application()  # Keep the application running while configuration is watched.
    finally:
        config.deinitialize()


def db_reconnect(host: str, port: int) -> None:
    """Placeholder for the database reconnection logic."""
    print(f"Reconnecting to database at {host}:{port}")


def run_application() -> None:
    """Placeholder for the main application logic."""
    import time

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
