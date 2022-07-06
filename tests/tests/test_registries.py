from unittest import TestCase

from opensearch_dsl import Index
from django_opensearch_dsl.registries import DocumentRegistry

from .fixtures import WithFixturesMixin


class DocumentRegistryTestCase(WithFixturesMixin, TestCase):
    def setUp(self):
        self.registry = DocumentRegistry()
        self.index_1 = Index(name='index_1')
        self.index_2 = Index(name='index_2')

        self.doc_a1 = self._generate_doc_mock(self.ModelA, self.index_1)
        self.doc_a2 = self._generate_doc_mock(self.ModelA, self.index_1)
        self.doc_b1 = self._generate_doc_mock(self.ModelB, self.index_2)
        self.doc_c1 = self._generate_doc_mock(self.ModelC, self.index_1)

    def test_update_related_instances(self):
        doc_d1 = self._generate_doc_mock(
            self.ModelD, self.index_1,
            _related_models=[self.ModelE, self.ModelB]
        )
        doc_d2 = self._generate_doc_mock(
            self.ModelD, self.index_1, _related_models=[self.ModelE]
        )

        instance_e = self.ModelE()
        instance_b = self.ModelB()
        related_instance = self.ModelD()

        doc_d2.get_instances_from_related.return_value = related_instance
        doc_d1.get_instances_from_related.return_value = related_instance
        self.registry.update_related(instance_e)

        doc_d1.get_instances_from_related.assert_called_once_with(instance_e)
        doc_d1.update.assert_called_once_with(related_instance)
        doc_d2.get_instances_from_related.assert_called_once_with(instance_e)
        doc_d2.update.assert_called_once_with(related_instance)

        doc_d1.get_instances_from_related.reset_mock()
        doc_d1.update.reset_mock()
        doc_d2.get_instances_from_related.reset_mock()
        doc_d2.update.reset_mock()

        self.registry.update_related(instance_b)
        doc_d1.get_instances_from_related.assert_called_once_with(instance_b)
        doc_d1.update.assert_called_once_with(related_instance)
        doc_d2.get_instances_from_related.assert_not_called()
        doc_d2.update.assert_not_called()

    def test_update_related_instances_not_defined(self):
        doc_d1 = self._generate_doc_mock(_model=self.ModelD, index=self.index_1,
                                         _related_models=[self.ModelE])

        instance = self.ModelE()

        doc_d1.get_instances_from_related.return_value = None
        self.registry.update_related(instance)

        doc_d1.get_instances_from_related.assert_called_once_with(instance)
        doc_d1.update.assert_not_called()
