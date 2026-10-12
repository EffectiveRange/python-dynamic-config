from argparse import _ArgumentGroup
from unittest import TestCase

from dynamic_config import ConfigArgumentParser, ConfigAction
from dynamic_config.parser import ConfigArgumentGroup, ConfigContainer


class TestConfigAction(TestCase):

    def test_dynamic_attribute_when_true(self):
        # When
        action = ConfigAction(dynamic=True, option_strings=["--test"], dest="test", nargs=None)

        # Then
        self.assertTrue(action.dynamic)

    def test_dynamic_attribute_when_false(self):
        # When
        action = ConfigAction(dynamic=False, option_strings=["--test"], dest="test", nargs=None)

        # Then
        self.assertFalse(action.dynamic)

    def test_dynamic_attribute_default(self):
        # When
        action = ConfigAction(option_strings=["--test"], dest="test", nargs=None)

        # Then
        self.assertFalse(action.dynamic)


class TestConfigContainer(TestCase):

    def test_add_dynamic_config_argument(self):
        # Given
        container = ConfigContainer(None, "-", None, "error")

        # When
        action = container.add_config_argument("--test", dynamic=True)

        # Then
        self.assertIsInstance(action, ConfigAction)
        self.assertTrue(action.dynamic)
        self.assertTrue(action in container._actions)

    def test_add_static_config_argument(self):
        # Given
        container = ConfigContainer(None, "-", None, "error")

        # When
        action = container.add_config_argument("--test", dynamic=False)

        # Then
        self.assertIsInstance(action, ConfigAction)
        self.assertFalse(action.dynamic)
        self.assertTrue(action in container._actions)

    def test_add_config_argument_default_dynamic(self):
        # Given
        container = ConfigContainer(None, "-", None, "error")

        # When
        action = container.add_config_argument("--test")

        # Then
        self.assertIsInstance(action, ConfigAction)
        self.assertFalse(action.dynamic)
        self.assertTrue(action in container._actions)


class TestConfigArgumentParser(TestCase):

    def test_add_argument(self):
        # Given
        parser = ConfigArgumentParser()

        # When
        parser.add_argument("--test")

        # Then
        self.assertTrue(any(action.dest == "test" for action in parser._actions))

    def test_add_config_argument(self):
        # Given
        parser = ConfigArgumentParser()

        # When
        parser.add_config_argument("--test")

        # Then
        action: ConfigAction = next(action for action in parser._actions if isinstance(action, ConfigAction))
        self.assertEqual(action.dest, "test")
        self.assertFalse(action.dynamic)

    def test_add_argument_group(self):
        # Given
        parser = ConfigArgumentParser()

        # When
        group = parser.add_argument_group("group")

        # Then
        self.assertEqual(group.title, "group")
        self.assertIsInstance(group, _ArgumentGroup)
        self.assertTrue(group in parser._action_groups)

    def test_add_config_argument_group(self):
        # Given
        parser = ConfigArgumentParser()

        # When
        group = parser.add_config_argument_group("group")

        # Then
        self.assertEqual(group.title, "group")
        self.assertIsInstance(group, ConfigArgumentGroup)
        self.assertTrue(group in parser._action_groups)

    def test_get_defaults_includes_group_actions(self):
        # Given
        parser = ConfigArgumentParser()

        parser.add_argument("--test0", default="test")
        parser.add_config_argument("--test1", default=None)
        parser.add_config_argument("--test2", default=1, type=int)
        group = parser.add_config_argument_group("group1")
        group.add_config_argument("--test3", default=None)
        group.add_config_argument("--test4", default=".", type=str)

        # When
        defaults = parser.get_defaults()

        # Then
        self.assertIn("test0", defaults)
        self.assertEqual(defaults["test0"], "test")
        self.assertNotIn("test1", defaults)
        self.assertIn("test2", defaults)
        self.assertEqual(defaults["test2"], 1)
        self.assertNotIn("test3", defaults)
        self.assertIn("test4", defaults)
        self.assertEqual(defaults["test4"], ".")

    def test_dump_defaults_includes_group_sections(self):
        # Given
        parser = ConfigArgumentParser()

        parser.add_argument("--test0", default="test")
        parser.add_config_argument("--test1", default="value1")
        group = parser.add_config_argument_group("group1")
        group.add_config_argument("--test2", default="value2")
        print()

        # When
        defaults = parser.default_config(print_to_console=True)

        # Then
        self.assertEqual(
            """
[default]
test1 = value1

[group1]
test2 = value2

""",
            f"\n{defaults}",
        )

    def test_parse_config(self):
        # Given
        parser = ConfigArgumentParser()
        parser.add_argument("--regular-in-default-group", default="regular_default")
        parser.add_config_argument("--string-in-default-group", default="value1")
        parser.add_config_argument("--int-in-default-group", type=int, default=2)
        parser.add_config_argument("--dynamic", dynamic=True, default="old_dynamic")
        parser.add_config_argument("--no-default")

        argument_group = parser.add_argument_group("arguments")
        argument_group.add_argument("--regular-grouped", default="regular_default")

        config_group = parser.add_config_argument_group("config")
        config_group.add_argument("--regular-in-config-group", default="regular_config_default")
        config_group.add_config_argument("--static-grouped", dynamic=False, default="old_static")
        config_group.add_config_argument("--dynamic-grouped", dynamic=True, type=int, default=4)
        config_group.add_config_argument("--omitted-default", default="fallback")
        config_group.add_config_argument("--omitted-no-default")

        config = {
            "regular_in_default_group": "ignored",
            "string_in_default_group": "new_value1",
            "int_in_default_group": "3",
            "dynamic": "new_dynamic",
            "no_default": "new_no_default",
            "regular_grouped": "ignored",
            "regular_in_config_group": "also_ignored",
            "static_grouped": "new_static",
            "dynamic_grouped": "5",
            "unknown": "ignored",
        }

        # When
        namespace = parser.parse_config(config)

        # Then
        self.assertEqual(namespace.regular_in_default_group, "regular_default")
        self.assertEqual(namespace.string_in_default_group, "new_value1")
        self.assertEqual(namespace.int_in_default_group, 3)
        self.assertEqual(namespace.dynamic, "new_dynamic")
        self.assertEqual(namespace.no_default, "new_no_default")
        self.assertEqual(namespace.regular_grouped, "regular_default")
        self.assertEqual(namespace.regular_in_config_group, "regular_config_default")
        self.assertEqual(namespace.static_grouped, "new_static")
        self.assertEqual(namespace.dynamic_grouped, 5)
        self.assertEqual(namespace.omitted_default, "fallback")
        self.assertFalse(hasattr(namespace, "omitted_no_default"))
        self.assertFalse(hasattr(namespace, "unknown"))
