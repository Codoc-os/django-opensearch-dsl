from copy import deepcopy
from typing import Any

from opensearchpy.helpers.index import Index as DSLIndex

from . import Document
from .apps import DODConfig
from .registries import registry


class Index(DSLIndex):
    """Creates an index and makes a deep copy of default index settings."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super(Index, self).__init__(*args, **kwargs)
        default_index_settings = deepcopy(DODConfig.default_index_settings())
        self.settings(**default_index_settings)

    def document(self, document: type[Document]) -> type[Document]:
        """Extend to register the document in the global document registry."""
        document = super(Index, self).document(document)
        registry.register_document(document)
        return document

    doc_type = document

    def __str__(self) -> str:
        return self._name
