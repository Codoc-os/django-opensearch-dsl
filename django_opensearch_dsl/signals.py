"""Attach django-opensearch-dsl to Django's signals and cause things to index."""

import abc

from django.apps import apps
from django.core.serializers import deserialize, serialize
from django.db import models
from django.dispatch import Signal

from .apps import DODConfig
from .registries import registry

# Sent after document indexing is completed
post_index = Signal()


class BaseSignalProcessor(abc.ABC):
    """Base signal processor.

    By default, does nothing with signals but provides underlying
    functionality.
    """

    def __init__(self, connections):
        self.connections = connections
        self.setup()

    @abc.abstractmethod
    def handle_save(self, sender, instance, **kwargs):
        """Update the instance in model and associated model indices."""

    @abc.abstractmethod
    def handle_pre_delete(self, sender, instance, **kwargs):
        """Delete the instance from model and associated model indices."""

    @abc.abstractmethod
    def handle_m2m_changed(self, sender, instance, action, **kwargs):
        """Handle changes in ManyToMany relations."""

    def setup(self):
        """Set up the SignalProcessor."""
        models.signals.post_save.connect(self.handle_save)
        models.signals.pre_delete.connect(self.handle_pre_delete)
        models.signals.m2m_changed.connect(self.handle_m2m_changed)

    def teardown(self):
        """Tear down the SignalProcessor."""
        models.signals.post_save.disconnect(self.handle_save)
        models.signals.pre_delete.disconnect(self.handle_pre_delete)
        models.signals.m2m_changed.disconnect(self.handle_m2m_changed)


class RealTimeSignalProcessor(BaseSignalProcessor):
    """Real-time signal processor.

    Allows for observing when saves/deletes fire and automatically updates the
    search engine appropriately.
    """

    def handle_save(self, sender, instance, **kwargs):
        """Update the instance in model and associated model indices."""
        registry.update(instance)
        registry.update_related(instance)

    def handle_pre_delete(self, sender, instance, **kwargs):
        """Delete the instance from model and associated model indices."""
        registry.delete(instance, raise_on_error=False)
        registry.delete_related(instance, raise_on_error=False)

    def handle_m2m_changed(self, sender, instance, action, **kwargs):
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
    def handle_save_task(app_label, model, pk):
        """Handle the update on the registry as a Celery task."""
        instance = apps.get_model(app_label, model).objects.get(pk=pk)
        registry.update(instance)
        registry.update_related(instance)

    @shared_task()
    def handle_pre_delete_task(data):
        """Delete the instance from model and associated model indices."""
        instance = next(deserialize("json", data, cls=DODConfig.signal_processor_deserializer_class())).object
        registry.delete(instance, raise_on_error=False)
        registry.delete_related(instance, raise_on_error=False)

    class CelerySignalProcessor(RealTimeSignalProcessor):
        """Celery signal processor.

        Allows automatic updates on the index as delayed background tasks using
        Celery.
        """

        def handle_save(self, sender, instance, **kwargs):
            """Update the instance in model and associated model indices."""
            handle_save_task(instance._meta.app_label, instance.__class__.__name__, instance.pk)

        def handle_pre_delete(self, sender, instance, **kwargs):
            """Delete the instance from model and associated model indices."""
            handle_pre_delete_task(serialize("json", [instance], cls=DODConfig.signal_processor_serializer_class()))
