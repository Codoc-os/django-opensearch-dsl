import enum


class CommandAction(str, enum.Enum):
    """Action available in commands."""

    INDEX = ("index", "indexing", "indexed")
    UPDATE = ("update", "updating", "updated")
    CREATE = ("create", "creating", "created")
    REBUILD = ("rebuild", "rebuilding", "rebuilt")
    LIST = ("list", "listing", "listed")
    DELETE = ("delete", "deleting", "deleted")
    MANAGE = ("manage", "managing", "managed")

    def __new__(cls, value: str, present_participle: str, past: str) -> "CommandAction":
        """Add additional attributes to the enum members."""
        obj = str.__new__(cls, value)
        obj._value_ = value
        obj.present_participle = present_participle
        obj.past = past
        return obj


class BulkAction(str, enum.Enum):
    """Enum for bulk actions."""

    INDEX = "index"
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
