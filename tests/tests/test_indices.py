from unittest import TestCase
from unittest.mock import patch

from django.conf import settings
from django.test import override_settings

from django_opensearch_dsl.indices import Index
from django_opensearch_dsl.registries import DocumentRegistry
from opensearch_dsl.connections import get_connection

from .fixtures import WithFixturesMixin


class IndexTestCase(WithFixturesMixin, TestCase):
    def setUp(self):
        self.registry = DocumentRegistry()
        get_connection().indices.delete(f"test{Index.VERSION_NAME_SEPARATOR}*")

    def test_documents_add_to_register(self):
        registry = self.registry
        with patch("django_opensearch_dsl.indices.registry", new=registry):
            index = Index("test")
            doc_a1 = self._generate_doc_mock(self.ModelA)
            index.document(doc_a1)
            indices = list(registry.get_indices())
            self.assertEqual(len(indices), 1)
            self.assertEqual(indices[0], index)

    def test__str__(self):
        index = Index("test")
        self.assertEqual(index.__str__(), "test")

    @override_settings(
        OPENSEARCH_DSL_INDEX_SETTINGS={
            "number_of_replicas": 0,
            "number_of_shards": 2,
        }
    )
    def test__init__(self):
        index = Index("test")
        self.assertEqual(
            index._settings,
            {
                "number_of_replicas": 0,
                "number_of_shards": 2,
            },
        )

    def test_versions_nominal(self):
        # GIVEN an Index that has not been created yet
        # (neither directly nor through versions)
        index = Index("test")
        self.assertFalse(index.exists())
        self.assertIsNone(index.get_active_version())
        self.assertEqual(index.get_versions(), [])

        # WHEN creating a new version of this index
        version_1 = index.create_new_version()

        # THEN it has been created but not activated
        self.assertFalse(index.exists())
        self.assertEqual(len(index.get_versions()), 1)
        self.assertTrue(version_1.exists())
        self.assertIsNone(index.get_active_version())

        # WHEN activating it
        index.activate_version(version_1._name)

        # THEN the index is marked as existing, it has an active version
        self.assertTrue(index.exists())
        self.assertEqual(version_1._name, index.get_active_version()._name)

        # WHEN creating another version of this index
        version_2 = index.create_new_version()

        # THEN it has been created but not activated
        self.assertEqual(len(index.get_versions()), 2)
        self.assertEqual(version_1._name, index.get_active_version()._name)
        self.assertTrue(version_1.exists())
        self.assertTrue(version_2.exists())

        # WHEN activating it
        index.activate_version(version_2._name)

        # THEN the index is marked as existing, it has an active version
        self.assertTrue(index.exists())
        self.assertEqual(version_2._name, index.get_active_version()._name)
