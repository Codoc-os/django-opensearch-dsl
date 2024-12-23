import sys
from typing import List

import opensearchpy
from django.core.management.base import OutputWrapper
from django.core.management.color import color_style

from django_opensearch_dsl.management.enums import OpensearchAction
from django_opensearch_dsl.registries import registry as default_registry


def manage_index(
    action,
    indices: List[str] = None,
    force: bool = False,
    ignore_error: bool = False,
    verbosity: int = 1,
    stderr=OutputWrapper(sys.stderr),
    stdout=OutputWrapper(sys.stdout),
    style=color_style(),
    registry=default_registry,
):  # noqa
    """Manage the creation and deletion of indices."""
    choices = [
        OpensearchAction.CREATE.value,
        OpensearchAction.DELETE.value,
        OpensearchAction.REBUILD.value,
        OpensearchAction.UPDATE.value,
    ]
    if action not in choices:
        raise ValueError(f"Invalid action '{action}'. Valid actions are: {', '.join(choices)}")

    action = OpensearchAction(action)
    known = registry.get_indices()

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

    # Display expected action
    if verbosity or not force:
        stdout.write(f"The following indices will be {action.past}:")
        for index in indices:
            stdout.write(f"\t- {index._name}.")  # noqa
        stdout.write("")

    # Ask for confirmation to continue
    if not force:  # pragma: no cover
        while True:
            p = input("Continue ? [y]es [n]o : ")
            if p.lower() in ["yes", "y"]:
                stdout.write("")
                break
            elif p.lower() in ["no", "n"]:
                exit(1)

    pp = action.present_participle.title()
    for index in indices:
        if verbosity:
            stdout.write(
                f"{pp} index '{index._name}'...\r",
                ending="",
            )  # noqa
            stdout.flush()
        try:
            # If current index depends on many different models, add them to
            # index._doc_types before indexing to make sure all mappings of different models
            # are taken into account.
            index_models = registry.get_indices_raw().get(index, None)
            for model in list(index_models):
                index._doc_types.append(model)

            if action == OpensearchAction.CREATE:
                index.create()
            elif action == OpensearchAction.DELETE:
                index.delete()
            elif action == OpensearchAction.UPDATE:
                index.put_mapping(body=index.to_dict()["mappings"])
            else:
                try:
                    index.delete()
                except opensearchpy.exceptions.NotFoundError:
                    pass
                index.create()
        except opensearchpy.exceptions.TransportError as e:
            if verbosity or not ignore_error:
                error = style.ERROR(f"Error: {e.error} - {e.info}")
                stderr.write(f"{pp} index '{index._name}'...\n{error}")  # noqa
            if not ignore_error:
                stderr.write("exiting...")
                exit(1)
        else:
            if verbosity:
                stdout.write(f"{pp} index '{index._name}'... {style.SUCCESS('OK')}")  # noqa
