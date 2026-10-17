from argparse import BooleanOptionalAction
from unittest import TestCase

from context_logger import setup_logging

from dynamic_config import ConfigArgumentParser, ConfigArgument
from dynamic_config.parser import ConfigArgumentGroup, ConfigContainer
from tests.utils import TEST_APPLICATION_NAME


class TestConfigContainer(TestCase):

    @classmethod
    def setUpClass(cls):
        setup_logging(TEST_APPLICATION_NAME, 'DEBUG', warn_on_overwrite=False)

    def setUp(self):
        print()

    def test_add_dynamic_config_argument(self):
        # Given
        container = ConfigContainer(None, "-", None, "error")

        # When
        argument = container.add_config_argument("--test", dynamic=True)

        # Then
        self.assertIsInstance(argument, ConfigArgument)
        self.assertTrue(argument.dynamic)
        self.assertEqual(container._arguments["test"], argument)

    def test_add_static_config_argument(self):
        # Given
        container = ConfigContainer(None, "-", None, "error")

        # When
        argument = container.add_config_argument("--test", dynamic=False)

        # Then
        self.assertIsInstance(argument, ConfigArgument)
        self.assertFalse(argument.dynamic)
        self.assertEqual(container._arguments["test"], argument)

    def test_add_config_argument_default_dynamic(self):
        # Given
        container = ConfigContainer(None, "-", None, "error")

        # When
        argument = container.add_config_argument("--test")

        # Then
        self.assertIsInstance(argument, ConfigArgument)
        self.assertFalse(argument.dynamic)
        self.assertEqual(container._arguments["test"], argument)

    def test_add_config_group(self):
        # Given
        container = ConfigContainer(None, "-", None, "error")

        # When
        group = container.add_config_group("group")

        # Then
        self.assertIsInstance(group, ConfigArgumentGroup)
        self.assertEqual(group.title, "group")
        self.assertTrue(group in container._action_groups)

    def test_get_config_groups(self):
        # Given
        container = ConfigContainer(None, "-", None, "error")
        group1 = container.add_config_group("group1")
        group2 = container.add_config_group("group2")

        # When
        groups = container.get_config_groups()

        # Then
        self.assertIn(group1, groups)
        self.assertIn(group2, groups)

    def test_get_config_arguments(self):
        # Given
        container = ConfigContainer(None, "-", None, "error")
        arg1 = container.add_config_argument("--test1", dynamic=True)
        arg2 = container.add_config_argument("--test2", dynamic=False)

        # When
        arguments = container.get_config_arguments()

        # Then
        self.assertIn("test1", arguments)
        self.assertIn("test2", arguments)
        self.assertEqual(arguments["test1"], arg1)
        self.assertEqual(arguments["test2"], arg2)

    def test_get_dynamic_arguments(self):
        # Given
        container = ConfigContainer(None, "-", None, "error")
        arg1 = container.add_config_argument("--test1", dynamic=True)
        container.add_config_argument("--test2", dynamic=False)

        # When
        dynamic_arguments = container.get_dynamic_arguments()

        # Then
        self.assertIn("test1", dynamic_arguments)
        self.assertNotIn("test2", dynamic_arguments)
        self.assertEqual(dynamic_arguments["test1"], arg1)


class TestConfigArgumentParser(TestCase):

    @classmethod
    def setUpClass(cls):
        setup_logging(TEST_APPLICATION_NAME, 'DEBUG', warn_on_overwrite=False)

    def setUp(self):
        print()

    def test_get_defaults_includes_group_actions(self):
        # Given
        parser = ConfigArgumentParser(default_section="default")

        parser.add_argument("--test0", default="test")
        parser.add_config_argument("--test1", default=None)
        parser.add_config_argument("--test2", default=1, type=int)
        group = parser.add_config_group("group1")
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

    def test_default_config_includes_group_sections(self):
        # Given
        parser = ConfigArgumentParser(default_section="default")

        parser.add_argument("--test0", default="test")
        parser.add_config_argument("--test1", default="value1")
        group = parser.add_config_group("group1")
        group.add_config_argument("--test2", default="value2")

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
        parser = ConfigArgumentParser(default_section="default")
        parser.add_argument("--regular-in-default-group", default="regular_default")
        parser.add_config_argument("--string-in-default-group", default="value1")
        parser.add_config_argument("--int-in-default-group", type=int, default=2)
        parser.add_config_argument("--dynamic", dynamic=True, default="old_dynamic")
        parser.add_config_argument("--no-default")
        parser.add_config_argument("--boolean-optional-true", dynamic=True, action=BooleanOptionalAction)
        parser.add_config_argument("--boolean-optional-false", dynamic=True, action=BooleanOptionalAction)

        argument_group = parser.add_argument_group("arguments")
        argument_group.add_argument("--regular-grouped", default="regular_default")

        config_group = parser.add_config_group("config")
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
            "boolean_optional_true": "yes",
            "boolean_optional_false": "no",
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
        self.assertTrue(namespace.boolean_optional_true)
        self.assertFalse(namespace.boolean_optional_false)
