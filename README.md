[![CI](https://github.com/EffectiveRange/python-dynamic-config/actions/workflows/ci.yaml/badge.svg)](https://github.com/EffectiveRange/python-dynamic-config/actions/workflows/ci.yaml)
[![Coverage badge](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/EffectiveRange/python-dynamic-config/python-coverage-comment-action-data/endpoint.json)](https://htmlpreview.github.io/?https://github.com/EffectiveRange/python-dynamic-config/blob/python-coverage-comment-action-data/htmlcov/index.html)

# python-dynamic-config
A Python library for loading configuration into a dynamic cache that is updated runtime on config file changes.

## Usage

```python
from argparse import BooleanOptionalAction
from pathlib import Path
from dynamic_config import ConfigArgumentParser, ConfigBuilder, ConfigChange

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

    live = config.get()
    snapshot = config.snapshot()
    # live.enabled follows future refreshes; snapshot.enabled retains this version.

    run_application()  # Keep the application running while configuration is watched.
finally:
    config.deinitialize()
```

For applications that receive command-line arguments through an entry point such as
`main(argv)`, pass that list to `.with_arguments(argv)` so the same arguments are
used during initialization and subsequent refreshes. Omitting the list preserves
the default behavior of parsing `sys.argv`.

For a runnable version of this example, see the [example app](examples/example_app).

An example configuration file:

```ini
[default]
port = 8080
enabled = yes

[security]
private_key = /etc/app/private.key
public_key = /etc/app/public.key

[database]
db_host = 127.0.0.1
db_port = 12345
```

The default configuration from the config argument defaults can be generated with
`default_config()` as a string or `default_config(print_to_console=True)` to also
print it to the standard output. This can be useful to provide a default config
file for reference, generated at build time and packaged with the application.

For a runnable example generator see the [example gen](examples/example_gen).

Sources are merged in builder order: later sources override earlier ones. Defaults
are included only when `with_defaults()` is used. Options omitted from a source
do not override earlier configuration values. Environment keys use the argument's
destination name in uppercase, for example `APP_ENABLED`.

Only arguments registered with `add_config_argument(..., dynamic=True)` change
during automatic refreshes. Removing a setting falls back to the remaining
sources (including defaults); when no source provides it, the dynamic attribute
is removed. Static settings retain their initialized values. An explicit
`refresh(dynamic_only=False)` replaces both static and dynamic settings.

Use `add_mutex_config_group()` to declare configuration arguments that are
mutually exclusive when parsing command-line arguments. The group's `required`
option follows argparse behavior; exclusivity is applied to command-line
parsing, not to values merged from configuration sources.

## Supported argument declarations

Configuration arguments must be named options, such as `--port`, and support:

- The default `store` action, with `type`, `choices`, and `nargs=None`, `?`, `+`,
  `*`, or a positive integer.
- `store_true`, `store_false`, and `argparse.BooleanOptionalAction`. File and
  environment values specify the resulting boolean directly, regardless of the
  action: `true`, `yes`, `1`, `on`, `false`, `no`, `0`, and `off`
  (case-insensitive). Other values are errors.
- Multi-value settings represented by shell-style quoted strings, such as
  `names = first "two words"`, or lists/tuples passed to `parse_config()`.
  Generated default configuration uses the same quoting convention.

Positional configuration arguments, custom actions, and actions such as
`append`, `count`, and `store_const` are rejected at registration. Ordinary
`add_argument()` declarations retain normal argparse command-line behavior;
required command-line arguments do not prevent loading a file or environment
source. Set boolean configuration defaults explicitly when needed.

Invalid file/environment values raise `ConfigError`, a `ValueError` subclass,
rather than exiting the application. Initialization and manual refresh propagate
errors to the caller. Automatic refresh logs failures and retains the last valid
configuration; subsequent valid edits can still be loaded. Command-line parsing
retains argparse's normal error/exit behavior.
Validation failures before observation starts can be corrected and initialization
retried. Observer startup failures shut down the instance and propagate the error.

## Refreshes, snapshots, and notifications

File watches monitor parent directories and filter events by configured paths,
so atomic file replacements and deletion/recreation continue to work. A watched
file may initially be absent, but its parent directory must exist. Watched
directories must exist when observation starts.

Publish complete updates with atomic replacement when possible. In-place writes
can expose intermediate valid contents (including an empty file), which are
treated as real configuration changes. Refresh serialization does not make
external writes, or updates spanning multiple files, atomic.

Refreshes are serialized through reading, merging, publishing, and change
detection. Readers see complete snapshots, never partially updated mappings.
Use `snapshot()` for a consistent version across multiple attribute reads.
Configuration values must support `copy.deepcopy`: mutable values are copied
on storage and retrieval, so modifying a returned list or dictionary changes
neither the live configuration nor an existing snapshot.

Register callbacks with `config.register(handler)` and remove them with
`config.deregister(handler)`. A handler receives `(file_path, changes)`, where
`changes` maps destination names to `ConfigChange` objects with `config_key`,
`old_value`, and `new_value`. Added/removed values use `None` for the absent side.
Each handler receives its own copy of the changes. Handlers execute
asynchronously and may run concurrently; completion order is not guaranteed.
Manual `refresh()` does not emit callbacks.

## Lifecycle

Always call `deinitialize()` when finished. It stops observation, drains pending
work, shuts down worker pools, and clears the live cache. Already obtained
snapshots remain valid. Shutdown is idempotent and terminal: build a new instance
to start again. `FileWatcher.stop()` has the same terminal lifecycle and is safe
before `start()`.

Run lifecycle operations on an owning/application thread, not inside change
handlers. Configuration initialization/de-initialization and watcher
watch/unwatch/start/stop calls from their own handlers raise `RuntimeError`
instead of risking a self-join deadlock. Shutdown waits for active handlers, so
handlers must finish without waiting for shutdown to complete.
