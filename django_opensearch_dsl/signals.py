"""Attach django-opensearch-dsl to Django's signals and cause things to index."""

import abc
from functools import partial
from typing import Any

from django.apps import apps
from django.core.serializers import deserialize, serialize
from django.db import models, transaction
from django.dispatch import Signal
from opensearchpy.connection.connections import Connections

from .apps import DODConfig
from .registries import registry

# Sent after document indexing is completed
post_index = Signal()


class BaseSignalProcessor(abc.ABC):
    """Base signal processor.

    By default, does nothing with signals but provides underlying
    functionality.
    """

    def __init__(self, connections: Connections):
        self.connections = connections
        self.setup()

    @abc.abstractmethod
    def handle_save(self, sender: type[models.Model], instance: models.Model, **kwargs: Any) -> None:
        """Update the instance in model and associated model indices."""

    @abc.abstractmethod
    def handle_pre_delete(self, sender: type[models.Model], instance: models.Model, **kwargs: Any) -> None:
        """Delete the instance from model and associated model indices."""

    @abc.abstractmethod
    def handle_m2m_changed(
        self, sender: type[models.Model], instance: models.Model, action: str, **kwargs: Any
    ) -> None:
        """Handle changes in ManyToMany relations."""

    def instance_requires_update(self, instance: models.Model) -> bool:
        """Check if an instance is connected to a Document (directly or related)."""
        m1 = instance._meta.model in registry._models
        m2 = instance.__class__.__base__ in registry._models
        m3 = bool(list(registry._get_related_doc(instance)))
        if m1 or m2 or m3:
            return True
        return False

    def setup(self) -> None:
        """Set up the SignalProcessor."""
        models.signals.post_save.connect(self.handle_save)
        models.signals.pre_delete.connect(self.handle_pre_delete)
        models.signals.m2m_changed.connect(self.handle_m2m_changed)

    def teardown(self) -> None:
        """Tear down the SignalProcessor."""
        models.signals.post_save.disconnect(self.handle_save)
        models.signals.pre_delete.disconnect(self.handle_pre_delete)
        models.signals.m2m_changed.disconnect(self.handle_m2m_changed)


class RealTimeSignalProcessor(BaseSignalProcessor):
    """Real-time signal processor.

    Allows for observing when saves/deletes fire and automatically updates the
    search engine appropriately.
    """

    def handle_save(self, sender: type[models.Model], instance: models.Model, **kwargs: Any) -> None:
        """Update the instance in model and associated model indices."""
        registry.update(instance)
        registry.update_related(instance)

    def handle_pre_delete(self, sender: type[models.Model], instance: models.Model, **kwargs: Any) -> None:
        """Delete the instance from model and associated model indices."""
        registry.delete(instance, raise_on_error=False)
        registry.delete_related(instance, raise_on_error=False)

    def handle_m2m_changed(
        self, sender: type[models.Model], instance: models.Model, action: str, **kwargs: Any
    ) -> None:
        """Handle changes in ManyToMany relations."""
        if action in ("post_add", "post_remove", "post_clear"):
            self.handle_save(sender, instance)
        elif action in ("pre_remove", "pre_clear"):
            self.handle_pre_delete(sender, instance)


try:
    from celery import shared_task
except ImportError:
    pass
else:

    @shared_task()
    def handle_save_task(app_label: str, model: str, pk: Any) -> None:
        """Handle the update on the registry as a Celery task."""
        model_object: models.Model = apps.get_model(app_label, model)
        try:
            instance = model_object.objects.get(pk=pk)
            registry.update(instance)
            registry.update_related(instance)
        except model_object.DoesNotExist:
            pass

    @shared_task()
    def handle_pre_delete_task(data: str) -> None:
        """Delete the instance from model and associated model indices."""
        instance = next(deserialize("json", data, cls=DODConfig.signal_processor_deserializer_class())).object
        registry.delete(instance, raise_on_error=False)
        registry.delete_related(instance, raise_on_error=False)

    class CelerySignalProcessor(RealTimeSignalProcessor):
        """Celery signal processor.

        Allows automatic updates on the index as delayed background tasks using
        Celery.
        """

        def handle_save(self, sender: type[models.Model], instance: models.Model, **kwargs: Any) -> None:
            """Update the instance in model and associated model indices."""
            if self.instance_requires_update(instance):
                transaction.on_commit(
                    partial(
                        handle_save_task.delay,
                        app_label=instance._meta.app_label,
                        model=instance.__class__.__name__,
                        pk=instance.pk,
                    )
                )

        def handle_pre_delete(self, sender: type[models.Model], instance: models.Model, **kwargs: Any) -> None:
            """Delete the instance from model and associated model indices."""
            if self.instance_requires_update(instance):
                handle_pre_delete_task.delay(
                    serialize(
                        "json",
                        [instance],
                        cls=DODConfig.signal_processor_serializer_class(),
                    )
                )
