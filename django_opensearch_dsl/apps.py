from django.apps import AppConfig
from django.conf import settings
from django.utils.module_loading import import_string
from opensearchpy.connection.connections import connections


class DODConfig(AppConfig):
    """Django Opensearch DSL Appconfig."""

    name = "django_opensearch_dsl"
    verbose_name = "django-opensearch-dsl"
    signal_processor = None

    def ready(self):
        """Autodiscover documents and register signals."""
        self.module.autodiscover()
        connections.configure(**settings.OPENSEARCH_DSL)

        # Set up the signal processor.
        if not self.signal_processor:
            self.signal_processor = self.signal_processor_class()(connections)

    @classmethod
    def autosync_enabled(cls):
        """Return whether auto sync is enabled."""
        return getattr(settings, "OPENSEARCH_DSL_AUTOSYNC", True)

    @classmethod
    def default_index_settings(cls):
        """Return `OPENSEARCH_DSL_INDEX_SETTINGS`."""
        return getattr(settings, "OPENSEARCH_DSL_INDEX_SETTINGS", {})

    @classmethod
    def auto_refresh_enabled(cls):
        """Return whether auto refresh is enabled."""
        return getattr(settings, "OPENSEARCH_DSL_AUTO_REFRESH", False)

    @classmethod
    def default_queryset_pagination(cls):
        """Return `OPENSEARCH_DSL_QUERYSET_PAGINATION`."""
        return getattr(settings, "OPENSEARCH_DSL_QUERYSET_PAGINATION", 4096)

    @classmethod
    def signal_processor_class(cls):
        """Import and return the target of `OPENSEARCH_SIGNAL_PROCESSOR_CLASS`."""
        path = getattr(
            settings, "OPENSEARCH_DSL_SIGNAL_PROCESSOR", "django_opensearch_dsl.signals.RealTimeSignalProcessor"
        )
        return import_string(path)

    @classmethod
    def signal_processor_serializer_class(cls):
        """Import and return the target of `OPENSEARCH_DSL_SIGNAL_PROCESSOR_SERIALIZER_CLASS`."""
        path = getattr(
            settings,
            "OPENSEARCH_DSL_SIGNAL_PROCESSOR_SERIALIZER_CLASS",
            "django.core.serializers.json.DjangoJSONEncoder",
        )
        return import_string(path)

    @classmethod
    def signal_processor_deserializer_class(cls):
        """Import and return the target of `OPENSEARCH_DSL_SIGNAL_PROCESSOR_SERIALIZER_CLASS`."""
        path = getattr(
            settings,
            "OPENSEARCH_DSL_SIGNAL_PROCESSOR_DESERIALIZER_CLASS",
            getattr(
                settings,
                "OPENSEARCH_DSL_SIGNAL_PROCESSOR_SERIALIZER_CLASS",
                "django.core.serializers.json.DjangoJSONEncoder",
            ),
        )
        return import_string(path)
