from copy import deepcopy
from datetime import datetime

from opensearch_dsl import Index as DSLIndex

from .apps import DODConfig
from .registries import registry


class Index(DSLIndex):
    """A specialized DSL index that can have versions."""

    VERSION_NAME_SEPARATOR = "--"

    def __init__(self, *args, **kwargs):
        """Creates an index and makes a deep copy of default index settings."""
        super(Index, self).__init__(*args, **kwargs)
        default_index_settings = deepcopy(DODConfig.default_index_settings())
        self.settings(**default_index_settings)

    def document(self, document):
        """Extend to register the document in the global document registry."""
        document = super(Index, self).document(document)
        registry.register_document(document)
        return document

    doc_type = document

    def get_versions(self, using=None):
        """Return a name-sorted list of Index objects named after this one."""
        return [
            Index(name)
            for name in sorted(
                self._get_connection(using=using)
                .indices.get(f"{self._name}{self.__class__.VERSION_NAME_SEPARATOR}*")
                .keys()
            )
        ]

    def get_version(self, version_name, using=None):
        """Return an Index that is a version of the current one."""
        for version in self.get_versions():
            if version._name == version_name:
                return version
        raise ValueError(f"Index version '{version_name}' not found for Index '{self._name}'")

    def get_active_version(self, using=None):
        """Return the concrete index that's active for this one."""
        for version in self.get_versions(using=using):
            if version.exists_alias(name=self._name):
                return version

        if self.exists():
            return self

    def create_new_version(self, suffix="", using=None):
        """Return a new Index, cloned from this one, with versioned name."""
        suffix = suffix or datetime.now().strftime("%Y%m%d%H%M%S%f")
        new_index = self.clone(f"{self._name}{self.__class__.VERSION_NAME_SEPARATOR}{suffix}")
        new_index.create(using=using)
        return new_index

    def activate_version(self, version_name, using=None):
        """Sets an alias to the Index on the given Index version."""
        index = self.get_version(version_name)

        actions_on_aliases = [
            {"add": {"index": index._name, "alias": self._name}},
        ]

        active_version = self.get_active_version(using=using)
        if active_version:
            actions_on_aliases.insert(
                0,
                {"remove": {"index": active_version._name, "alias": self._name}},
            )

        self._get_connection(using=using).indices.update_aliases(body={"actions": actions_on_aliases})

    def __str__(self):
        return self._name
