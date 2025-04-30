import argparse
import functools
import operator
import sys
from argparse import ArgumentParser
from collections import defaultdict
from typing import Any, Callable

from django.core.exceptions import FieldError
from django.core.management import BaseCommand
from django.db.models import Q

from django_opensearch_dsl.registries import registry

from ...utils import manage_document, manage_index
from ..enums import OpensearchAction
from ..types import parse


class Command(BaseCommand):
    """Manage indices and documents."""

    help = (
        "Allow to create and delete indices, as well as indexing, updating or deleting specific "
        "documents from specific indices.\n"
    )

    def __init__(self, *args, **kwargs):  # noqa
        super(Command, self).__init__()
        self.usage = None

    def db_filter(self, parser: ArgumentParser) -> Callable[[str], Any]:
        """Return a function to parse the filters."""

        def wrap(value):  # pragma: no cover
            try:
                lookup, v = value.split("=")
                v = parse(v)
            except ValueError:
                sys.stderr.write(parser._subparsers._group_actions[0].choices["document"].format_usage())  # noqa
                sys.stderr.write(
                    f"manage.py index: error: invalid filter: '{value}' (filter must be formatted as "
                    f"'[Field Lookups]=[value]')\n",
                )
                exit(1)
            return lookup, v  # noqa

        return wrap

    def __list_index(self, **options):  # noqa pragma: no cover
        """List all known index and indicate whether they are created or not."""
        indices = registry.get_indices()
        result = defaultdict(list)
        for index in indices:
            module = index._doc_types[0].__module__.split(".")[-2]  # noqa
            exists = index.exists()
            checkbox = f"[{'X' if exists else ' '}]"
            count = f" ({index.search().count()} documents)" if exists else ""
            result[module].append(f"{checkbox} {index._name}{count}")
        for app, indices in result.items():
            self.stdout.write(self.style.MIGRATE_LABEL(app))
            self.stdout.write("\n".join(indices))

    def _manage_index(self, action, indices, force, verbosity, ignore_error, **options):  # noqa
        """Manage the creation and deletion of indices."""
        manage_index(
            action, indices, force, ignore_error, verbosity, stderr=self.stderr, stdout=self.stdout, style=self.style
        )

    def _manage_document(
        self,
        action,
        indices,
        objects,
        force,
        filters,
        excludes,
        verbosity,
        parallel,
        count,
        refresh,
        missing,
        database,
        batch_size,
        batch_type,
        **options,
    ):  # noqa
        """Manage the creation and deletion of indices."""
        manage_document(
            action=action,
            indices=indices,
            objects=objects,
            filters=filters,
            excludes=excludes,
            force=force,
            parallel=parallel,
            count=count,
            refresh=refresh,
            missing=missing,
            database=database,
            batch_size=batch_size,
            batch_type=batch_type,
            verbosity=verbosity,
            stderr=self.stderr,
            stdout=self.stdout,
            style=self.style,
        )

    def add_arguments(self, parser):
        """Add arguments to parser."""
        parser.formatter_class = argparse.RawTextHelpFormatter
        subparsers = parser.add_subparsers()

        # 'list' subcommand
        subparser = subparsers.add_parser(
            "list",
            help="Show all available indices (and their state) for the current project.",
            description="Show all available indices (and their state) for the current project.",
        )
        subparser.set_defaults(func=self.__list_index)

        # 'index' subcommand
        subparser = subparsers.add_parser(
            "index",
            help="Manage the creation an deletion of indices.",
            description="Manage the creation an deletion of indices.",
        )
        subparser.set_defaults(func=self._manage_index)
        subparser.add_argument(
            "action",
            type=str,
            help=(
                "Whether you want to create, update, delete or rebuild the indices.\n"
                "Update allow you to update your indices mappings if you modified them after creation. "
                "This should be done prior to indexing new document with dynamic mapping (enabled by default), "
                "a default mapping with probably the wrong type would be created for any new field."
            ),
            choices=[
                OpensearchAction.CREATE.value,
                OpensearchAction.DELETE.value,
                OpensearchAction.REBUILD.value,
                OpensearchAction.UPDATE.value,
            ],
        )
        subparser.add_argument("--force", action="store_true", default=False, help="Do not ask for confirmation.")
        subparser.add_argument("--ignore-error", action="store_true", default=False, help="Do not stop on error.")
        subparser.add_argument(
            "indices",
            type=str,
            nargs="*",
            metavar="INDEX",
            help="Only manage the given indices.",
        )

        # 'document' subcommand
        subparser = subparsers.add_parser(
            "document",
            help="Manage the indexation and creation of documents.",
            description="Manage the indexation and creation of documents.",
            formatter_class=argparse.RawTextHelpFormatter,
        )
        subparser.set_defaults(func=self._manage_document)
        subparser.add_argument(
            "action",
            type=str,
            help="Whether you want to create, delete or rebuild the indices.",
            choices=[
                OpensearchAction.INDEX.value,
                OpensearchAction.DELETE.value,
                OpensearchAction.UPDATE.value,
            ],
        )
        subparser.add_argument(
            "-d",
            "--database",
            type=str,
            default=None,
            help="Nominates a database to use as source.",
        )
        subparser.add_argument(
            "-f",
            "--filters",
            type=self.db_filter(parser),
            nargs="*",
            help=(
                "Filter object in the queryset. Argument must be formatted as '[lookup]=[value]', e.g. "
                "'document_date__gte=2020-05-21.\n"
                "The accepted value type are:\n"
                "  - 'None' ('[lookup]=')\n"
                "  - 'float' ('[lookup]=1.12')\n"
                "  - 'int' ('[lookup]=23')\n"
                "  - 'datetime.date' ('[lookup]=2020-10-08')\n"
                "  - 'list' ('[lookup]=1,2,3,4') Value between comma ',' can be of any other accepted value type\n"
                "  - 'str' ('[lookup]=week') Value that didn't match any type above will be interpreted as a str\n"
                "The list of lookup function can be found here: "
                "https://docs.djangoproject.com/en/dev/ref/models/querysets/#field-lookups"
            ),
        )
        subparser.add_argument(
            "-e",
            "--excludes",
            type=self.db_filter(parser),
            nargs="*",
            help=(
                "Exclude objects from the queryset. Argument must be formatted as '[lookup]=[value]', see '--filters' "
                "for more information"
            ),
        )
        subparser.add_argument("--force", action="store_true", default=False, help="Do not ask for confirmation.")
        subparser.add_argument(
            "-i", "--indices", type=str, nargs="*", help="Only update documents on the given indices."
        )
        subparser.add_argument("-o", "--objects", type=str, nargs="*", help="Only update selected objects.")
        subparser.add_argument(
            "-c", "--count", type=int, default=None, help="Update at most COUNT objects (0 to index everything)."
        )
        subparser.add_argument(
            "-p",
            "--parallel",
            action="store_true",
            default=False,
            help="Parallelize the communication with Opensearch.",
        )
        subparser.add_argument(
            "-r",
            "--refresh",
            action="store_true",
            default=False,
            help="Make operations performed on the indices immediatly available for search.",
        )
        subparser.add_argument(
            "-m",
            "--missing",
            action="store_true",
            default=False,
            help="When used with 'index' action, only index documents not indexed yet.",
        )
        subparser.add_argument(
            "-b",
            "--batch-size",
            type=int,
            default=None,
            help="Specify the batch size for processing documents.",
        )
        subparser.add_argument(
            "-t",
            "--batch-type",
            type=str,
            default="offset",
            help="Specify the batch type for processing documents (pk_filters | offset).",
        )

        self.usage = parser.format_usage()

    def handle(self, *args, **options):
        """Run the command according to `options`."""
        if "func" not in options:  # pragma: no cover
            self.stderr.write(self.usage)
            self.stderr.write(f"manage.py opensearch: error: no subcommand provided.")
            exit(1)

        options["func"](**options)
