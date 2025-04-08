import io
import sys
import time
import copy
from collections import deque
from functools import partial
from typing import Iterable, Optional

from django.db import models
from django.db.models import Max, Min, Q, QuerySet
from opensearchpy.helpers import bulk, parallel_bulk
from opensearchpy.helpers.document import Document as DSLDocument

from . import fields
from .apps import DODConfig
from .exceptions import ModelFieldNotMappedError
from .management.enums import OpensearchAction
from .search import Search
from .signals import post_index

model_field_class_to_field_class = {
    models.AutoField: fields.IntegerField,
    models.BigAutoField: fields.LongField,
    models.BigIntegerField: fields.LongField,
    models.BooleanField: fields.BooleanField,
    models.CharField: fields.TextField,
    models.DateField: fields.DateField,
    models.DateTimeField: fields.DateField,
    models.DecimalField: fields.DoubleField,
    models.EmailField: fields.TextField,
    models.FileField: fields.FileField,
    models.FilePathField: fields.KeywordField,
    models.FloatField: fields.DoubleField,
    models.ImageField: fields.FileField,
    models.IntegerField: fields.IntegerField,
    models.NullBooleanField: fields.BooleanField,
    models.PositiveIntegerField: fields.IntegerField,
    models.PositiveSmallIntegerField: fields.ShortField,
    models.SlugField: fields.KeywordField,
    models.SmallIntegerField: fields.ShortField,
    models.TextField: fields.TextField,
    models.TimeField: fields.LongField,
    models.URLField: fields.TextField,
    models.UUIDField: fields.KeywordField,
}


class Document(DSLDocument):
    """Allow the definition of Opensearch' index using Django `Model`."""

    _prepared_fields = []

    def __init__(self, related_instance_to_ignore=None, **kwargs):
        super(Document, self).__init__(**kwargs)
        # related instances to ignore is required to remove the instance
        # from related models on deletion.
        self._related_instance_to_ignore = related_instance_to_ignore
        self._prepared_fields = self.init_prepare()

    @classmethod
    def search(cls, using=None, index=None):
        """Return a `Search` object parametrized with the index' information."""
        return Search(
            using=cls._get_using(using), index=cls._default_index(index), doc_type=[cls], model=cls.django.model
        )

    def get_queryset(
        self, db_alias: str = None, filter_: Optional[Q] = None, exclude: Optional[Q] = None, count: int = None
    ) -> QuerySet:
        """Return the queryset that should be indexed by this doc type."""
        qs = self.django.model.objects.using(db_alias).all()

        if filter_:
            qs = qs.filter(filter_)
        if exclude:
            qs = qs.exclude(exclude)
        if count is not None:
            qs = qs[:count]

        return qs

    def _eta(self, start, done, total):  # pragma: no cover
        if done == 0:
            return "~"
        eta = round((time.time() - start) / done * (total - done))
        unit = "secs"
        if eta > 120:
            eta //= 60
            unit = "mins"
        return f"{eta} {unit}"

    def get_indexing_queryset(
            self,
            db_alias: str = None,
            verbose: bool = False,
            filter_: Optional[Q] = None,
            exclude: Optional[Q] = None,
            count: int = None,
            action: OpensearchAction = OpensearchAction.INDEX,
            stdout: io.FileIO = sys.stdout,
            batch_size: int = None,
            batch_type: str = "offset",
    ) -> Iterable:
        """Divide the queryset into chunks."""
        chunk_size = batch_size or self.django.queryset_pagination
        qs = self.get_queryset(db_alias=db_alias, filter_=filter_, exclude=exclude, count=count)
        qs = qs.order_by("pk")
        count = qs.count()
        model = self.django.model.__name__
        action = action.present_participle.title()
        start = time.time()
        done = 0
        if verbose:
            stdout.write(f"{action} {model}: 0% ({self._eta(start, done, count)})\r")

        if batch_type == "pk_filters":
            pks = qs.aggregate(min=Min("pk"), max=Max("pk"))
            total_batches = (pks["max"] - pks["min"]) // chunk_size
            for batch_number, offset in enumerate(range(pks["min"], pks["max"] + 1, chunk_size), start=1):
                batch_qs = list(copy.deepcopy(qs.filter(pk__gte=offset, pk__lt=offset + chunk_size)))
                stdout.write(f"Processing batch {batch_number}/{total_batches}: \n")
                for obj in batch_qs:
                    done += 1
                    if done % chunk_size == 0:
                        stdout.write(f"{action} {model}: {round(done / count * 100)}% ({self._eta(start, done, count)})\r")
                    yield obj
                if len(batch_qs) > 0:
                    stdout.write(f"Max primary key in the current batch: {batch_qs[-1].pk}\n")
        else:
            total_batches = (count + chunk_size - 1) // chunk_size
            for batch_number, offset in enumerate(range(0, count, chunk_size), start=1):
                batch_qs = list(copy.deepcopy(qs[offset: offset + chunk_size].all()))
                stdout.write(f"Processing batch {batch_number}/{total_batches}: \n")
                for obj in batch_qs:
                    done += 1
                    if done % chunk_size == 0:
                        stdout.write(
                            f"{action} {model}: {round(done / count * 100)}% ({self._eta(start, done, count)})\r")
                    yield obj
                if len(batch_qs) > 0:
                    stdout.write(f"Max primary key in the current batch: {batch_qs[-1].pk}\n")


    def init_prepare(self):
        """Initialise the data model preparers once here.

        Extracts the preparers from the model and generate a list of callables
        to avoid doing that work on every object instance over.
        """
        index_fields = getattr(self, "_fields", {})
        preparers = []
        for name, field in iter(index_fields.items()):
            if not isinstance(field, fields.DODField):  # pragma: no cover
                continue

            if not field._path:  # noqa
                field._path = [name]

            prep_func = getattr(self, "prepare_%s_with_related" % name, None)
            if prep_func:
                fn = partial(prep_func, related_to_ignore=self._related_instance_to_ignore)
            else:
                prep_func = getattr(self, "prepare_%s" % name, None)
                if prep_func:
                    fn = prep_func
                else:
                    fn = partial(field.get_value_from_instance, field_value_to_ignore=self._related_instance_to_ignore)

            preparers.append((name, field, fn))

        return preparers

    def prepare(self, instance):
        """Generate the opensearch's document from `instance` based on defined fields."""
        data = {name: prep_func(instance) for name, field, prep_func in self._prepared_fields}
        return data

    @classmethod
    def to_field(cls, field_name, model_field):
        """Return the opensearch field instance mapped to the model field class.

        This is a good place to hook into if you have more complex
        model field to OS field logic.
        """
        try:
            return model_field_class_to_field_class[model_field.__class__](attr=field_name)
        except KeyError:  # pragma: no cover
            raise ModelFieldNotMappedError(f"Cannot convert model field {field_name} to an Opensearch field!")

    def bulk(self, actions, using=None, **kwargs):
        """Execute given actions in bulk."""
        response = bulk(client=self._get_connection(using), actions=actions, **kwargs)
        # send post index signal
        post_index.send(sender=self.__class__, instance=self, actions=actions, response=response)
        return response

    def parallel_bulk(self, actions, using=None, **kwargs):
        """Parallel version of `bulk`."""
        kwargs.setdefault("chunk_size", self.django.queryset_pagination)
        bulk_actions = parallel_bulk(client=self._get_connection(using), actions=actions, **kwargs)
        # As the `parallel_bulk` is lazy, we need to get it into `deque` to run
        # it instantly.
        # See https://discuss.elastic.co/t/helpers-parallel-bulk-in-python-not-working/39498/2  # noqa
        deque(bulk_actions, maxlen=0)
        # Fake return value to emulate bulk() since we don't have a result yet,
        # the result is currently not used upstream anyway.
        return 1, []

    @classmethod
    def generate_id(cls, object_instance):
        """Generate the opensearch's _id from a Django `Model` instance.

        The default behavior is to use the Django object's pk (id) as the
        opensearch index id (_id). If needed, this method can be overloaded
        to change this default behavior.
        """
        return object_instance.pk

    def _prepare_action(self, object_instance, action):
        return {
            "_op_type": action,
            "_index": self._index._name,  # noqa
            "_id": self.generate_id(object_instance),
            "_source" if action != "update" else "doc": (self.prepare(object_instance) if action != "delete" else None),
        }

    def _get_actions(self, object_list, action):
        for object_instance in object_list:
            if action == "delete" or self.should_index_object(object_instance):
                yield self._prepare_action(object_instance, action)

    def _bulk(self, *args, parallel=False, using=None, **kwargs):
        """Allow switching between normal and parallel bulk operation."""
        if parallel:
            return self.parallel_bulk(*args, using=using, **kwargs)
        return self.bulk(*args, using=using, **kwargs)

    def should_index_object(self, obj):
        """Whether given object should be indexed.

        Overwriting this method and returning a boolean value should determine
        whether the object should be indexed.
        """
        return True

    def update(self, thing, action, *args, refresh=None, using=None, **kwargs):  # noqa
        """Update document in OS for a model, iterable of models or queryset."""
        if refresh is None:
            refresh = getattr(self.Index, "auto_refresh", DODConfig.auto_refresh_enabled())

        if isinstance(thing, models.Model):
            object_list = [thing]
        else:
            object_list = thing

        return self._bulk(self._get_actions(object_list, action), *args, refresh=refresh, using=using, **kwargs)
