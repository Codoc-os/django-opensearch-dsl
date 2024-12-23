import argparse
import functools
import operator
import sys
from argparse import ArgumentParser
from collections import defaultdict
from typing import Any, Callable, List, Tuple

from django.core.exceptions import FieldError
from django.core.management import BaseCommand
from django.core.management.base import OutputWrapper
from django.core.management.color import color_style
from django.db.models import Q

from django_opensearch_dsl.management.enums import OpensearchAction
from django_opensearch_dsl.management.types import parse
from django_opensearch_dsl.registries import registry as default_registry


def manage_document(
    action,
    filters: List[Tuple[str, Any]] = None,
    excludes: List[Tuple[str, Any]] = None,
    indices: List[str] = None,
    objects: List[str] = None,
    parallel: bool = False,
    refresh: bool = False,
    missing: bool = False,
    force: bool = False,
    database: str = None,
    batch_type: str = "offset",
    batch_size: int = None,
    count: int = None,
    verbosity: int = 1,
    stderr=OutputWrapper(sys.stderr),
    stdout=OutputWrapper(sys.stdout),
    style=color_style(),
    registry=default_registry,
):  # noqa
    """Manage the creation and deletion of indices."""
    choices = [OpensearchAction.INDEX.value, OpensearchAction.DELETE.value, OpensearchAction.UPDATE.value]
    if action not in choices:
        raise ValueError(f"Invalid action '{action}'. Valid actions are: {', '.join(choices)}")

    action = OpensearchAction(action)
    known = registry.get_indices()
    filter_ = functools.reduce(operator.and_, (Q(**{k: v}) for k, v in filters)) if filters else None
    exclude = functools.reduce(operator.and_, (Q(**{k: v}) for k, v in excludes)) if excludes else None

    # Filter existing objects
    valid_models = []
    registered_models = [m.__name__.lower() for m in registry.get_models()]
    if objects:
        for model in objects:
            if model.lower() in registered_models:
                valid_models.append(model)
            else:
                stderr.write(f"Unknown object '{model}', choices are: '{registered_models}'")
                exit(1)

    # Filter indices
    if indices:
        # Ensure every given indices exists
        known_name = [i._name for i in known]  # noqa
        unknown = set(indices) - set(known_name)
        if unknown:
            stderr.write(f"Unknown indices '{list(unknown)}', choices are: '{known_name}'")
            exit(1)

        # Only keep given indices
        indices = list(filter(lambda i: i._name in indices, known))  # noqa
    else:
        indices = known

    # Ensure every indices needed are created
    not_created = [i._name for i in indices if not i.exists()]  # noqa
    if not_created:
        stderr.write(f"The following indices are not created : {not_created}")
        stderr.write("Use 'python3 manage.py opensearch list' to list indices' state.")
        exit(1)

    # Check field, preparing to display expected actions
    s = f"The following documents will be {action.past}:"
    kwargs_list = []

    if objects:
        django_models = [m for m in registry.get_models() if m.__name__.lower() in valid_models]
        all_os_models = []
        selected_os_models = []
        indices_raw = registry.get_indices_raw()

        for k, v in indices_raw.items():
            for model in list(v):
                all_os_models.append(model)

        for os_model in all_os_models:
            if os_model.django.model in django_models and os_model.Index.name in list(i._name for i in indices):
                selected_os_models.append(os_model)

        # Handle --missing
        exclude_ = exclude
        for model in selected_os_models:
            try:
                kwargs_list.append({"filter_": filter_, "exclude": exclude_, "count": count})
                qs = model().get_queryset(filter_=filter_, exclude=exclude_, count=count).count()
            except FieldError as e:
                stderr.write(f"Error while filtering on '{model.django.model.__name__}':\n{e}'")  # noqa
                exit(1)
            else:
                s += f"\n\t- {qs} {model.django.model.__name__}."
    else:
        for index in indices:
            # Handle --missing
            exclude_ = exclude
            if missing and action == OpensearchAction.INDEX:
                q = Q(pk__in=[h.meta.id for h in index.search().extra(stored_fields=[]).scan()])
                exclude_ = exclude_ & q if exclude_ is not None else q

            document = index._doc_types[0]()  # noqa
            try:
                kwargs_list.append({"db_alias": database, "filter_": filter_, "exclude": exclude_, "count": count})
                qs = document.get_queryset(filter_=filter_, exclude=exclude_, count=count).count()
            except FieldError as e:
                model = index._doc_types[0].django.model.__name__  # noqa
                stderr.write(f"Error while filtering on '{model}' (from index '{index._name}'):\n{e}'")  # noqa
                exit(1)
            else:
                s += f"\n\t- {qs} {document.django.model.__name__}."

    # Display expected actions
    if verbosity or not force:
        stdout.write(s + "\n\n")

    # Ask for confirmation to continue
    if not force:  # pragma: no cover
        while True:
            p = input("Continue ? [y]es [n]o : ")
            if p.lower() in ["yes", "y"]:
                stdout.write("\n")
                break
            elif p.lower() in ["no", "n"]:
                exit(1)

    result = "\n"
    if objects:
        for model, kwargs in zip(selected_os_models, kwargs_list):
            document = model()  # noqa
            qs = document.get_indexing_queryset(
                stdout=stdout._out,
                verbose=verbosity,
                action=action,
                batch_size=batch_size,
                batch_type=batch_type,
                **kwargs,
            )
            success, errors = document.update(
                qs, parallel=parallel, refresh=refresh, action=action, raise_on_error=False
            )

            success_str = style.SUCCESS(success) if success else success
            errors_str = style.ERROR(len(errors)) if errors else len(errors)
            model = document.django.model.__name__

            if verbosity == 1:
                result += f"{success_str} {model} successfully {action.past}, {errors_str} errors:\n"
                reasons = defaultdict(int)
                for e in errors:  # Count occurrence of each error
                    error = e.get(action, {"result": "unknown error"}).get("result", "unknown error")
                    reasons[error] += 1
                for reasons, total in reasons.items():
                    result += f"    - {reasons} : {total}\n"

            if verbosity > 1:
                result += f"{success_str} {model} successfully {action}d, {errors_str} errors:\n {errors}\n"

    else:
        for index, kwargs in zip(indices, kwargs_list):
            document = index._doc_types[0]()  # noqa
            qs = document.get_indexing_queryset(
                stdout=stdout._out,
                verbose=verbosity,
                action=action,
                batch_size=batch_size,
                batch_type=batch_type,
                **kwargs,
            )
            success, errors = document.update(
                qs, parallel=parallel, refresh=refresh, action=action, raise_on_error=False
            )

            success_str = style.SUCCESS(success) if success else success
            errors_str = style.ERROR(len(errors)) if errors else len(errors)
            model = document.django.model.__name__

            if verbosity == 1:
                result += f"{success_str} {model} successfully {action.past}, {errors_str} errors:\n"
                reasons = defaultdict(int)
                for e in errors:  # Count occurrence of each error
                    error = e.get(action, {"result": "unknown error"}).get("result", "unknown error")
                    reasons[error] += 1
                for reasons, total in reasons.items():
                    result += f"    - {reasons} : {total}\n"

            if verbosity > 1:
                result += f"{success_str} {model} successfully {action}d, {errors_str} errors:\n {errors}\n"

    if verbosity:
        stdout.write(result + "\n")
