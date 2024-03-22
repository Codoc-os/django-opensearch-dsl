Settings
========

## `OPENSEARCH_DSL`

**Required**

`OPENSEARCH_DSL` is used to configure the connections to opensearch. It must at least define a `'default'` connection
with a given `'hosts'`:

```python
OPENSEARCH_DSL = {
    'default': {
        'hosts': 'localhost:9200'
    }
}
```

`OPENSEARCH_DSL` is passed
to [`opensearchpy.connection.connections.configure()`](http://elasticsearch-dsl.readthedocs.io/en/stable/configuration.html#multiple-clusters)
.

## `OPENSEARCH_DSL_INDEX_SETTINGS`

Default: `{}`

Additional options passed to the `opensearch-py` Index settings (like `number_of_replicas` or `number_of_shards`).
See [Opensearch's index settings](https://opensearch.org/docs/latest/opensearch/rest-api/index-apis/create-index/#index-settings)
for more information.

## `OPENSEARCH_DSL_AUTO_REFRESH`

Default: `False`

Set to `True` to force
an [index refresh](https://www.elastic.co/guide/en/elasticsearch/reference/current/indices-refresh.html>) with update.

## `OPENSEARCH_DSL_PARALLEL`

Default: `False`

Run indexing in parallel using OpenSearch's parallel_bulk() method. Note that some databases (e.g. SQLite)
do not play well with this option.

## `OPENSEARCH_DSL_QUERYSET_PAGINATION`

Default: `4096`

Size of the chunk used when indexing data. Can be overridden by setting `queryset_pagination` inside `Document`'
s [`Django` subclass](document.md).


## `OPENSEARCH_DSL_AUTOSYNC`

Default: `True`

Set to `False` to globally disable auto-syncing.

See [Autosync](document.md#autosync) for more information.

The autosync operations can be customized using [`OPENSEARCH_DSL_SIGNAL_PROCESSOR`](settings.md#opensearch_dsl_signal_processor)
setting.

## `OPENSEARCH_DSL_SIGNAL_PROCESSOR`

Default: `django_opensearch_dsl.signals.RealTimeSignalProcessor`.

This (optional) setting controls what SignalProcessor class is used to handle Django’s signals and
keep the indices up-to-date. While some builtin choices are provided, you can also define your own
by subclassing `django_opensearch_dsl.signals.BaseSignalProcessor`.

Builtin choices are:

* `django_opensearch_dsl.signals.RealTimeSignalProcessor`

Operations are processed synchronously as soon as the signal is emitted.

* `django_opensearch_dsl.signals.CelerySignalProcessor`

Uses Celery to process the operations asynchronously.

## `OPENSEARCH_DSL_SIGNAL_PROCESSOR_SERIALIZER_CLASS`

Default: `django.core.serializers.json.DjangoJSONEncoder`.

When using asynchronous signal processor such as `CelerySignalProcessor`, the instance will probably be deleted from the
database by the time the operation is processed. Since `django-opensearch-dsl` need a relies on the database to do most
of its operation, the instance will be serialized by the signal and deserialized by the processor to keep a valid
instance.

This serialization process can be customized using this setting.
See [Django's serialization documentation](https://docs.djangoproject.com/en/5.0/topics/serialization/#serialization-formats-json)
for more information.

## `OPENSEARCH_DSL_SIGNAL_PROCESSOR_DESERIALIZER_CLASS`

Default: `OPENSEARCH_DSL_SIGNAL_PROCESSOR_SERIALIZER_CLASS`.

Use by the processor to deserialize the data serialized by the signal.
See [`OPENSEARCH_DSL_SIGNAL_PROCESSOR_SERIALIZER_CLASS`](settings.md#opensearch_dsl_signal_processor_serializer_class)
for more information.
