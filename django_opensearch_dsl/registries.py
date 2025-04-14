from collections import defaultdict
from copy import deepcopy
from itertools import chain
from typing import TYPE_CHECKING, Any, Generator, Iterable

from django.core.exceptions import ImproperlyConfigured, ObjectDoesNotExist
from django.db.models import Model
from opensearchpy import Index
from opensearchpy.helpers.utils import AttrDict

from .apps import DODConfig
from .enums import BulkAction
from .exceptions import RedeclaredFieldError

if TYPE_CHECKING:
    from .documents import Document


class DocumentRegistry:
    """Registry of models classes to a set of Document classes."""

    def __init__(self) -> None:
        self._indices: defaultdict[Index, set[type["Document"]]] = defaultdict(set)
        self._models: defaultdict[type[Model], set[type["Document"]]] = defaultdict(set)
        self._related_models: defaultdict[type[Model], set[type[Model]]] = defaultdict(set)

    def register(self, index: Index, doc_class: type["Document"]) -> None:
        """Register the model with the registry."""
        self._models[doc_class.django.model].add(doc_class)

        for related in doc_class.django.related_models:
            self._related_models[related].add(doc_class.django.model)

        for idx, docs in self._indices.items():
            if index._name == idx._name:  # noqa pragma: no cover
                docs.add(doc_class)
                return

        self._indices[index].add(doc_class)

    def register_document(self, doc_class: type["Document"]) -> type["Document"]:
        """Register given document within the registry."""
        django_meta = getattr(doc_class, "Django")
        # Raise error if Django class can not be found
        if not django_meta:  # pragma: no cover
            message = f"You must declare the Django class inside {doc_class.__name__}"
            raise ImproperlyConfigured(message)

        # Keep all django related attribute in a django_attr AttrDict
        django_attr = AttrDict(
            {
                "model": getattr(doc_class.Django, "model"),
                "queryset_pagination": getattr(
                    doc_class.Django, "queryset_pagination", DODConfig.default_queryset_pagination()
                ),
                "ignore_signals": getattr(django_meta, "ignore_signals", False),
                "auto_refresh": getattr(django_meta, "auto_refresh", DODConfig.auto_refresh_enabled()),
                "related_models": getattr(django_meta, "related_models", []),
            }
        )
        if not django_attr.model:  # pragma: no cover
            raise ImproperlyConfigured("You must specify the django model")

        # Add The model fields into opensearch mapping field
        model_field_names = getattr(doc_class.Django, "fields", [])
        mapping_fields = doc_class._doc_type.mapping.properties.properties.to_dict().keys()  # noqa

        for field_name in model_field_names:
            if field_name in mapping_fields:  # pragma: no cover
                raise RedeclaredFieldError(
                    f"You cannot redeclare the field named '{field_name}' on {doc_class.__name__}"
                )

            django_field = django_attr.model._meta.get_field(field_name)  # noqa

            field_instance = doc_class.to_field(field_name, django_field)
            doc_class._doc_type.mapping.field(field_name, field_instance)  # noqa

        # Add django attribute with all the django attribute
        setattr(doc_class, "django", django_attr)

        # Set the fields of the mappings
        fields = doc_class._doc_type.mapping.properties.properties.to_dict()  # noqa
        setattr(doc_class, "_fields", fields)

        # Update settings of the document index
        default_index_settings = deepcopy(DODConfig.default_index_settings())
        doc_class._index.settings(**{**default_index_settings, **doc_class._index._settings})  # noqa

        # Register the document and index class to our registry
        self.register(index=doc_class._index, doc_class=doc_class)  # noqa

        return doc_class

    def _get_related_doc(self, instance: Model) -> Generator[type["Document"], None, None]:
        for model in self._related_models.get(instance.__class__, []):
            for doc in self._models[model]:
                if (
                    instance.__class__ in doc.django.related_models
                    or instance.__class__.__base__ in doc.django.related_models
                ):
                    yield doc

    def update_related(self, instance: Model, action: BulkAction = BulkAction.INDEX, **kwargs: Any) -> None:
        """Update documents related to `instance`.

        Related documents are found using the `get_instances_from_related()`
        method of each Document classes including the instance's Model is
        including within their `related_models`.
        """
        if not DODConfig.autosync_enabled():
            return
        for doc in self._get_related_doc(instance):
            doc_instance = doc()
            try:
                related = doc_instance.get_instances_from_related(instance)
            except ObjectDoesNotExist:
                related = None

            if related is not None:
                doc_instance.update(related, action, **kwargs)

    def delete_related(self, instance: Model, action: BulkAction = BulkAction.INDEX, **kwargs: Any) -> None:
        """Remove `instance` from related models.

        `related_instance_to_ignore` ensures that `instance` is only removed
        from related models. We don't want to update the indexed value for
        `instance` in this method. Prevents potential orphaned objects.
        """
        if not DODConfig.autosync_enabled():
            return

        for doc in self._get_related_doc(instance):
            doc_instance = doc(related_instance_to_ignore=instance)
            try:
                related = doc_instance.get_instances_from_related(instance)
            except ObjectDoesNotExist:
                related = None

            if related is not None:
                doc_instance.update(related, action, **kwargs)

    def update(self, instance: Model, action: BulkAction = BulkAction.INDEX, **kwargs: Any) -> None:
        """Update all the opensearch documents attached to this model.

        Only update if settings' `OPENSEARCH_DSL_AUTOSYNC` is `True` and
        `Document'`s `ignore_signals` is `False`.
        """
        if not DODConfig.autosync_enabled():
            return

        if instance.__class__ in self._models:
            for doc in self._models[instance.__class__]:
                if not doc.django.ignore_signals:
                    doc().update(instance, action, **kwargs)

        if instance.__class__.__base__ in self._models:
            for doc in self._models[instance.__class__.__base__]:
                if not doc.django.ignore_signals:
                    doc().update(instance, action, **kwargs)

    def delete(self, instance: Model, **kwargs: Any) -> None:
        """Delete all the opensearch documents attached to this model.

        Only delete if settings' `OPENSEARCH_DSL_AUTOSYNC` is `True` and
        `Document'`s `ignore_signals` is `False`.
        """
        self.update(instance, action=BulkAction.DELETE, **kwargs)

    def get_documents(self, models: Iterable[Model] = None) -> set[type["Document"]]:
        """Get all documents in the registry or the documents for a list of models."""
        if models is not None:
            docs_iter = (self._models[model] for model in models if model in self._models)
        else:
            docs_iter = (model for model in self._models.values())
        return set(chain.from_iterable(docs_iter))

    def get_models(self) -> set[type[Model]]:
        """Get all models in the registry."""
        return set(self._models.keys())

    def get_indices(self, models: Iterable[Model] = None) -> set[Index]:
        """Get all indices in the registry or the indices for a list of models."""
        if models is not None:
            return set(index for index, docs in self._indices.items() for doc in docs if doc.django.model in models)

        return set(self._indices.keys())

    def __contains__(self, instance: type[Model]) -> bool:
        """Check that a model is in the registry."""
        if issubclass(instance, Model):
            return instance in self._models or instance in self._related_models
        raise TypeError(
            f"'in <{type(self).__name__}>' requires a Model subclass as left operand, not {type(dict).__name__}"
        )


registry = DocumentRegistry()
