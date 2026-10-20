from argparse import BooleanOptionalAction, Namespace
from concurrent.futures import ThreadPoolExecutor
from configparser import ConfigParser
from threading import Event
from unittest.mock import Mock

import pytest
from watchdog.events import FileModifiedEvent, FileMovedEvent
from watchdog.observers.api import BaseObserver, ObservedWatch

from dynamic_config import (
    ArgumentSource,
    ConfigArgumentParser,
    ConfigCache,
    ConfigError,
    DefaultSource,
    DynamicConfig,
    FileSource,
    FileWatcher,
    Source,
    Watcher,
)


@pytest.fixture
def make_config():
    configs = []

    def make(parser, sources, initial=None):
        config = DynamicConfig(ConfigCache(initial), parser, Mock(spec=Watcher), sources)
        configs.append(config)
        return config

    yield make
    for config in configs:
        config.deinitialize()


@pytest.fixture
def make_watcher():
    watchers = []

    def make():
        observer = Mock(spec=BaseObserver)
        observer.is_alive.return_value = False
        observer.schedule.side_effect = lambda handler, path, recursive: ObservedWatch(path, recursive=recursive)
        watcher = FileWatcher(observer)
        watchers.append(watcher)
        return watcher

    yield make
    for watcher in watchers:
        watcher.stop()


@pytest.mark.parametrize("action", ["store_true", "store_false", BooleanOptionalAction])
@pytest.mark.parametrize("value, expected", [("yes", True), ("off", False), (True, True), (0, False)])
def test_boolean_actions_parse_explicit_values(action, value, expected):
    # Given
    parser = ConfigArgumentParser()
    parser.add_config_argument("--enabled", action=action)

    # When
    explicit = parser.parse_config({"enabled": value})
    empty_config = parser.parse_config({})
    empty_arguments = parser.parse_args([])

    # Then
    assert explicit.enabled is expected
    assert vars(empty_config) == {}
    assert vars(empty_arguments) == {}


@pytest.mark.parametrize("action", ["store_true", "store_false", BooleanOptionalAction])
def test_boolean_actions_reject_typos(action):
    # Given
    parser = ConfigArgumentParser()
    parser.add_config_argument("--enabled", action=action)

    # When / Then
    with pytest.raises(ConfigError, match="invalid boolean"):
        parser.parse_config({"enabled": "tru"})


@pytest.mark.parametrize(
    "kwargs, value",
    [
        ({"type": int}, "bad"),
        ({"choices": ["valid"]}, "bad"),
        ({"nargs": 2}, "one"),
        ({"nargs": "+"}, ""),
        ({"nargs": "+"}, '"unterminated'),
        ({"nargs": "+"}, 42),
    ],
)
def test_invalid_config_raises_without_exiting(kwargs, value, capsys):
    # Given
    parser = ConfigArgumentParser()
    parser.add_config_argument("--value", **kwargs)

    # When / Then
    with pytest.raises(ConfigError):
        parser.parse_config({"value": value})
    assert capsys.readouterr().err == ""


@pytest.mark.parametrize(
    "nargs, value, expected",
    [
        ("+", 'one "two words"', ["one", "two words"]),
        ("*", "", []),
        (2, [1, 2], ["1", "2"]),
        (None, "--literal-value", "--literal-value"),
        ("?", "", ""),
    ],
)
def test_scalar_and_sequence_values(nargs, value, expected):
    # Given
    parser = ConfigArgumentParser()
    parser.add_config_argument("--value", nargs=nargs)

    # When
    config = parser.parse_config({"value": value})

    # Then
    assert config.value == expected


def test_sequence_types_and_registered_types():
    # Given
    parser = ConfigArgumentParser()
    parser.register("type", "number", int)
    parser.add_config_argument("--values", nargs="+", type="number", choices=[1, 2])

    # When
    config = parser.parse_config({"values": "1 2"})

    # Then
    assert config.values == [1, 2]


@pytest.mark.parametrize(
    "args, kwargs",
    [
        (("value",), {}),
        (("--value",), {"action": "append"}),
        (("--value",), {"action": "count"}),
        (("--value",), {"nargs": "..."}),
    ],
)
def test_unsupported_declarations_fail_at_registration(args, kwargs):
    # Given
    parser = ConfigArgumentParser()

    # When / Then
    with pytest.raises(ValueError):
        parser.add_config_argument(*args, **kwargs)
    assert not parser.get_config_arguments()


def test_config_parsing_ignores_required_command_line_arguments():
    # Given
    parser = ConfigArgumentParser()
    parser.add_argument("command")
    parser.add_argument("--required", required=True)
    parser.add_config_argument("--value", type=int)

    # When
    config = parser.parse_config({"value": "42"})

    # Then
    assert config.value == 42

    # When / Then
    with pytest.raises(SystemExit):
        parser.parse_args([])


def test_default_sequence_roundtrip():
    # Given
    parser = ConfigArgumentParser()
    parser.add_config_argument("--values", nargs="+", default=["one", "two words"])
    ini = ConfigParser(interpolation=None)

    # When
    ini.read_string(parser.default_config())
    config = parser.parse_config(dict(ini["default"]))

    # Then
    assert config.values == ["one", "two words"]


def test_absent_flags_do_not_override_sources(make_config, monkeypatch):
    # Given
    parser = ConfigArgumentParser()
    parser.add_config_argument("--enabled", action="store_true", default=False, dynamic=True)
    source = Mock(spec=Source)
    source.get_config.return_value = parser.parse_config({"enabled": "true"})
    monkeypatch.setattr("sys.argv", ["app"])
    config = make_config(parser, [DefaultSource(parser), source, ArgumentSource(parser)])

    # When
    config.refresh(False)

    # Then
    assert config.get().enabled is True


def test_refresh_removes_missing_dynamic_keys_and_preserves_static(make_config):
    # Given
    parser = ConfigArgumentParser()
    parser.add_config_argument("--dynamic", dynamic=True)
    parser.add_config_argument("--static")
    source = Mock(spec=Source)
    source.get_config.return_value = Namespace()
    config = make_config(parser, [source], {"dynamic": "old", "static": "fixed"})
    changed = Event()
    handler = Mock(side_effect=lambda path, changes: changed.set())
    config.register(handler)

    # When
    config._on_config_file_change("config.conf")

    # Then
    assert changed.wait(3)
    assert config.snapshot().values() == {"static": "fixed"}
    change = handler.call_args.args[1]["dynamic"]
    assert (change.old_value, change.new_value) == ("old", None)


def test_removal_falls_back_to_defaults(make_config):
    # Given
    parser = ConfigArgumentParser()
    parser.add_config_argument("--value", default="fallback", dynamic=True)
    config = make_config(parser, [DefaultSource(parser)], {"value": "override"})

    # When
    config.refresh()

    # Then
    assert config.get().value == "fallback"


def test_full_refresh_replaces_removed_static_values(make_config):
    # Given
    parser = ConfigArgumentParser()
    config = make_config(parser, [], {"static": "old"})

    # When
    config.refresh(False)

    # Then
    assert config.snapshot().values() == {}


def test_overlapping_refreshes_are_serialized(make_config):
    # Given
    parser = ConfigArgumentParser()
    parser.add_config_argument("--value", dynamic=True)
    old_read = Event()
    release_old = Event()
    new_attempt = Event()
    new_read = Event()
    calls = []

    def get_config():
        calls.append(True)
        if len(calls) == 1:
            old_read.set()
            assert release_old.wait(3)
            return Namespace(value="old")
        new_read.set()
        return Namespace(value="new")

    source = Mock(spec=Source)
    source.get_config.side_effect = get_config
    config = make_config(parser, [source])

    def newer_refresh():
        new_attempt.set()
        config.refresh()

    with ThreadPoolExecutor(2) as executor:
        # When
        older = executor.submit(config.refresh)
        try:
            assert old_read.wait(3)
            newer = executor.submit(newer_refresh)
            assert new_attempt.wait(3)

            # Then
            assert not new_read.wait(0.1)
        finally:
            # When
            release_old.set()
        older.result(3)
        newer.result(3)

    # Then
    assert config.get().value == "new"


def test_invalid_reload_logs_preserves_snapshot_and_recovers(make_config, make_watcher, tmp_path):
    # Given
    path = tmp_path / "config.conf"
    path.write_text("[app]\nvalue = bad\n")
    parser = ConfigArgumentParser()
    parser.add_config_argument("--value", type=int, dynamic=True)
    config = make_config(parser, [FileSource(parser, path)], {"value": 1})
    watcher = make_watcher()
    watcher.log = Mock()

    # When
    watcher._execute_handler(config._on_config_file_change, str(path))

    # Then
    assert config.get().value == 1
    error = watcher.log.warn.call_args.kwargs["error"]
    assert isinstance(error, ConfigError)

    # When
    path.write_text("[app]\nvalue = 2\n")
    watcher._execute_handler(config._on_config_file_change, str(path))

    # Then
    assert config.get().value == 2


def test_overlapping_events_emit_one_coherent_change(make_config):
    # Given
    parser = ConfigArgumentParser()
    parser.add_config_argument("--value", dynamic=True)
    first_read = Event()
    release = Event()
    source = Mock(spec=Source)

    def get_config():
        first_read.set()
        assert release.wait(3)
        return Namespace(value="new")

    source.get_config.side_effect = get_config
    config = make_config(parser, [source], {"value": "old"})
    handler = Mock()
    config.register(handler)

    # When
    with ThreadPoolExecutor(2) as executor:
        first = executor.submit(config._on_config_file_change, "first.conf")
        try:
            assert first_read.wait(3)
            second = executor.submit(config._on_config_file_change, "second.conf")
        finally:
            release.set()
        first.result(3)
        second.result(3)
    config._executor.shutdown(wait=True)

    # Then
    handler.assert_called_once()
    change = handler.call_args.args[1]["value"]
    assert (change.old_value, change.new_value) == ("old", "new")


def test_change_values_are_isolated_between_handlers(make_config):
    # Given
    parser = ConfigArgumentParser()
    parser.add_config_argument("--names", dynamic=True)
    source = Mock(spec=Source)
    source.get_config.return_value = Namespace(names=["new"])
    config = make_config(parser, [source], {"names": ["old"]})
    mutated = Event()
    observed = []

    def mutate(path, changes):
        changes["names"].new_value.append("handler mutation")
        mutated.set()

    def observe(path, changes):
        if mutated.wait(3):
            observed.append(changes["names"].new_value)

    config.register(mutate)
    config.register(observe)

    # When
    config._on_config_file_change("config.conf")
    config._executor.shutdown(wait=True)

    # Then
    assert observed == [["new"]]
    assert config.get().names == ["new"]


def test_failed_initialization_is_recoverable(make_config, tmp_path):
    # Given
    path = tmp_path / "config.conf"
    path.write_text("[app]\nvalue = bad\n")
    parser = ConfigArgumentParser()
    parser.add_config_argument("--value", type=int)
    config = make_config(parser, [FileSource(parser, path)])

    # When / Then
    with pytest.raises(ConfigError):
        config.initialize()
    config._watcher.start.assert_not_called()

    # When
    path.write_text("[app]\nvalue = 2\n")
    config.initialize()

    # Then
    assert config.get().value == 2


def test_observer_start_failure_cleans_up_configuration(make_config):
    # Given
    config = make_config(ConfigArgumentParser(), [], {"value": "old"})
    config._watcher.start.side_effect = OSError("Cannot start observer")

    # When / Then
    with pytest.raises(OSError, match="Cannot start observer"):
        config.initialize()
    config._watcher.stop.assert_called_once()
    config._watcher.deregister.assert_called_once_with(config._on_config_file_change)
    assert config.snapshot().values() == {}

    # When / Then
    with pytest.raises(RuntimeError, match="de-initialized"):
        config.initialize()


def test_initialization_is_idempotent(make_config):
    # Given
    config = make_config(ConfigArgumentParser(), [])

    # When
    config.initialize()
    config.initialize()

    # Then
    config._watcher.start.assert_called_once()


def test_shutdown_waits_for_handlers_and_is_terminal(make_config):
    # Given
    parser = ConfigArgumentParser()
    parser.add_config_argument("--value", dynamic=True)
    source = Mock(spec=Source)
    source.get_config.return_value = Namespace(value="new")
    config = make_config(parser, [source], {"value": "old"})
    entered = Event()
    release = Event()
    stopping = Event()

    def handler(path, changes):
        entered.set()
        assert release.wait(3)

    config.register(handler)
    config._on_config_file_change("config.conf")
    assert entered.wait(3)
    config._watcher.stop.side_effect = stopping.set

    with ThreadPoolExecutor(1) as executor:
        # When
        shutdown = executor.submit(config.deinitialize)
        try:
            assert stopping.wait(3)

            # Then
            assert not shutdown.done()
            with pytest.raises(RuntimeError, match="de-initialized"):
                config.refresh()
            config._on_config_file_change("late-event.conf")
        finally:
            # When
            release.set()
        shutdown.result(3)

    # Then
    assert config.snapshot().values() == {}
    assert all(not thread.is_alive() for thread in config._executor._threads)

    # When
    config.deinitialize()

    # Then
    config._watcher.stop.assert_called_once()

    # When / Then
    with pytest.raises(RuntimeError, match="de-initialized"):
        config.initialize()


def test_handler_cannot_shutdown_its_own_executor(make_config):
    # Given
    config = make_config(ConfigArgumentParser(), [])
    config._callback.active = True

    # When / Then
    try:
        with pytest.raises(RuntimeError, match="outside"):
            config.deinitialize()
    finally:
        config._callback.active = False


def test_watcher_filters_files_and_handles_move_destinations(make_watcher, tmp_path):
    # Given
    watcher = make_watcher()
    path = tmp_path / "config.conf"
    watcher.watch(path)
    handler = Mock()
    watcher.register(handler)

    # When
    watcher.on_any_event(FileModifiedEvent(str(tmp_path / "unrelated.conf")))

    # Then
    handler.assert_not_called()

    # When
    watcher.on_any_event(FileMovedEvent(str(tmp_path / "temporary"), str(path)))
    watcher.stop()

    # Then
    handler.assert_called_once_with(str(path))
    watcher._observer.schedule.assert_called_once_with(watcher, str(tmp_path), recursive=False)


def test_shared_directory_watch_survives_unwatch(make_watcher, tmp_path):
    # Given
    watcher = make_watcher()
    first = tmp_path / "first.conf"
    second = tmp_path / "second.conf"
    watcher.watch(first)
    watcher.watch(second)
    handler = Mock()
    watcher.register(handler)

    # When
    watcher.unwatch(first)

    # Then
    watcher._observer.unschedule.assert_not_called()

    # When
    watcher.on_any_event(FileModifiedEvent(str(second)))
    watcher.stop()

    # Then
    handler.assert_called_once_with(str(second))


@pytest.mark.parametrize("recursive", [False, True])
def test_directory_filter_respects_recursion(make_watcher, tmp_path, recursive):
    # Given
    watcher = make_watcher()
    watcher.watch(tmp_path, recursive=recursive)
    handler = Mock()
    watcher.register(handler)
    direct = str(tmp_path / "direct.conf")
    nested = str(tmp_path / "sub" / "nested.conf")

    # When
    watcher.on_any_event(FileModifiedEvent(direct))
    watcher.on_any_event(FileModifiedEvent(nested))
    watcher.stop()

    # Then
    assert sorted(call.args[0] for call in handler.call_args_list) == sorted(
        [direct, nested] if recursive else [direct]
    )


def test_file_paths_are_normalized_without_resolving_symlinks(make_watcher, tmp_path):
    # Given
    watcher = make_watcher()
    watcher.watch(tmp_path / "sub" / ".." / "config.conf")
    handler = Mock()
    watcher.register(handler)

    # When
    watcher.on_any_event(FileModifiedEvent(str(tmp_path / "config.conf")))
    watcher.stop()

    # Then
    handler.assert_called_once()


def test_watcher_stop_drains_callbacks_and_rejects_restart(make_watcher, tmp_path):
    # Given
    watcher = make_watcher()
    path = tmp_path / "config.conf"
    watcher.watch(path)
    entered = Event()
    release = Event()
    stopping = Event()

    def handler(path):
        entered.set()
        assert release.wait(3)

    watcher.register(handler)
    watcher.on_any_event(FileModifiedEvent(str(path)))
    assert entered.wait(3)
    watcher._observer.stop.side_effect = stopping.set

    with ThreadPoolExecutor(1) as executor:
        # When
        shutdown = executor.submit(watcher.stop)
        try:
            assert stopping.wait(3)

            # Then
            assert not shutdown.done()

            # When
            watcher.on_any_event(FileModifiedEvent(str(path)))
        finally:
            release.set()
        shutdown.result(3)

    # Then
    assert all(not thread.is_alive() for thread in watcher._executor._threads)

    # When / Then
    with pytest.raises(RuntimeError, match="stopped"):
        watcher.start()


def test_nested_values_are_defensively_copied():
    # Given
    initial = {"options": {"names": ["first"]}}
    cache = ConfigCache(initial)
    snapshot = cache.snapshot()

    # When
    initial["options"]["names"].append("input mutation")
    snapshot.options["names"].append("snapshot mutation")
    cache.get().options["names"].append("live mutation")
    snapshot.values()["options"]["names"].append("mapping mutation")

    # Then
    assert snapshot.options == {"names": ["first"]}
    assert cache.get().options == {"names": ["first"]}

    # When
    cache.update({"options": {"names": ["second"]}})

    # Then
    assert snapshot.options == {"names": ["first"]}
    assert cache.get().options == {"names": ["second"]}
    assert snapshot == snapshot
    assert cache == cache


def test_failed_value_copy_does_not_publish_partial_configuration():
    # Given
    class Uncopyable:
        def __deepcopy__(self, memo):
            raise ValueError("Cannot copy value")

    cache = ConfigCache({"value": "original"})

    # When / Then
    with pytest.raises(ValueError, match="Cannot copy value"):
        cache.replace({"value": Uncopyable()})
    assert cache.get().value == "original"
