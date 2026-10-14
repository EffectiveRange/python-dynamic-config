from unittest import TestCase

from dynamic_config.cache import ConfigCache, ConfigSnapshot


class TestConfigSnapshot(TestCase):

    def test_get(self):
        # Given
        snapshot = ConfigSnapshot({"key": "value"})

        # When
        result = snapshot.key

        # Then
        self.assertEqual(result, "value")

    def test_immutable_set(self):
        # Given
        snapshot = ConfigSnapshot({"key": "value"})

        # When / Then
        with self.assertRaises(AttributeError):
            snapshot.key = "new_value"

    def test_immutable_del(self):
        # Given
        snapshot = ConfigSnapshot({"key": "value"})

        # When / Then
        with self.assertRaises(AttributeError):
            del snapshot.key

    def test_values_method(self):
        # Given
        snapshot = ConfigSnapshot({"key": "value"})

        # When
        result = snapshot.values()

        # Then
        self.assertEqual(result, {"key": "value"})


class TestConfigCache(TestCase):

    def test_get(self):
        # Given
        cache = ConfigCache({"key": "value"})

        # When
        result = cache.key

        # Then
        self.assertEqual(result, "value")

    def test_get_missing(self):
        # Given
        cache = ConfigCache({"key": "value"})

        # When / Then
        with self.assertRaises(AttributeError):
            cache.missing_key

    def test_immutable_set(self):
        # Given
        cache = ConfigCache()

        # When / Then
        with self.assertRaises(AttributeError):
            cache.key = "new_value"

    def test_snapshot(self):
        # Given
        cache = ConfigCache({"key": "value"})

        # When
        snapshot = cache.snapshot()

        # Then
        self.assertEqual(snapshot.values(), {"key": "value"})

    def test_update(self):
        # Given
        cache = ConfigCache({"key": "value"})

        # When
        cache.update({"key": "new_value"})

        # Then
        self.assertEqual(cache.key, "new_value")

    def test_update_creates_new_snapshot(self):
        # Given
        cache = ConfigCache({"key": "value"})
        old_snapshot = cache.snapshot()
        cache.update({"key": "new_value"})

        # When
        new_snapshot = cache.snapshot()

        # Then
        self.assertNotEqual(old_snapshot, new_snapshot)
        self.assertEqual(old_snapshot.values(), {"key": "value"})
        self.assertEqual(new_snapshot.values(), {"key": "new_value"})
