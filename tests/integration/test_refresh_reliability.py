import os
from threading import Event

from dynamic_config import ConfigArgumentParser, ConfigBuilder


def test_atomic_replacement_subsequent_edits_and_recreation(tmp_path):
    # Given
    path = tmp_path / "config.conf"
    path.write_text("[app]\nvalue = original\n")
    parser = ConfigArgumentParser()
    parser.add_config_argument("--value", dynamic=True)
    config = ConfigBuilder(parser).with_file(path).build()
    changed = Event()
    expected = ["replacement"]

    def handler(file_path, changes):
        change = changes.get("value")
        if change is not None and change.new_value == expected[0]:
            changed.set()

    config.register(handler)
    try:
        config.initialize()
        replacement = tmp_path / "temporary.conf"
        replacement.write_text("[app]\nvalue = replacement\n")

        # When
        os.replace(replacement, path)

        # Then
        assert changed.wait(3)
        assert config.get().value == "replacement"

        # Given
        expected[0] = "edited"
        changed.clear()

        # When
        path.write_text("[app]\nvalue = edited\n")

        # Then
        assert changed.wait(3)
        assert config.get().value == "edited"

        # Given
        expected[0] = None
        changed.clear()

        # When
        path.unlink()

        # Then
        assert changed.wait(3)
        assert "value" not in config.get()

        # Given
        expected[0] = "recreated"
        changed.clear()

        # When
        path.write_text("[app]\nvalue = recreated\n")

        # Then
        assert changed.wait(3)
        assert config.get().value == "recreated"
    finally:
        config.deinitialize()


def test_invalid_file_retains_last_valid_configuration_and_recovers(tmp_path):
    # Given
    path = tmp_path / "config.conf"
    path.write_text("[app]\nvalue = 1\n")
    parser = ConfigArgumentParser()
    parser.add_config_argument("--value", type=int, dynamic=True)
    config = ConfigBuilder(parser).with_file(path).build()
    rejected = Event()
    changed = Event()
    original_handler = config._on_config_file_change

    def observe_failure(file_path):
        try:
            original_handler(file_path)
        except ValueError:
            rejected.set()
            raise

    config._on_config_file_change = observe_failure
    config.register(lambda path, changes: changed.set())
    try:
        config.initialize()
        replacement = tmp_path / "temporary.conf"
        replacement.write_text("[app]\nvalue = invalid\n")

        # When
        os.replace(replacement, path)

        # Then
        assert rejected.wait(3)
        assert config.get().value == 1
        assert not changed.is_set()
        # Given
        replacement.write_text("[app]\nvalue = 2\n")

        # When
        os.replace(replacement, path)

        # Then
        assert changed.wait(3)
        assert config.get().value == 2
    finally:
        config.deinitialize()
