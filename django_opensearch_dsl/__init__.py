from django.utils.module_loading import autodiscover_modules

from .documents import Document  # noqa
from .fields import *  # noqa

__version__ = "0.6.2"


def autodiscover():
    """Force the import of the `documents` modules of each `INSTALLED_APPS`."""
    autodiscover_modules("documents")
