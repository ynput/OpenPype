# Metadata keys for work with studio and project overrides
M_OVERRIDEN_KEY = "__overriden_keys__"
# Metadata key for storing information about environments
M_ENVIRONMENT_KEY = "__environment_keys__"
# Metadata key for storing dynamic created labels
M_DYNAMIC_KEY_LABEL = "__dynamic_keys_labels__"

METADATA_KEYS = (
    M_OVERRIDEN_KEY,
    M_ENVIRONMENT_KEY,
    M_DYNAMIC_KEY_LABEL
)

# File where studio's system overrides are stored
SYSTEM_SETTINGS_KEY = "system_settings"
PROJECT_SETTINGS_KEY = "project_settings"
PROJECT_ANATOMY_KEY = "project_anatomy"

WRAPPER_TYPES = ["form", "collapsible-wrap"]

__all__ = (
    "M_OVERRIDEN_KEY",
    "M_ENVIRONMENT_KEY",
    "M_DYNAMIC_KEY_LABEL",

    "METADATA_KEYS",

    "SYSTEM_SETTINGS_KEY",
    "PROJECT_SETTINGS_KEY",
    "PROJECT_ANATOMY_KEY"
)


class OverrideStateItem:
    values = set()

    def __init__(self, value, name):
        self.name = name
        if value in self.__class__.values:
            raise ValueError(
                "Implementation bug: Override State with same value as other."
            )
        self.__class__.values.add(value)
        self.value = value

    def __repr__(self):
        return "<object {}> {} {}".format(
            self.__class__.__name__, self.value, self.name
        )

    def __eq__(self, other):
        """Defines behavior for the equality operator, ==."""
        if isinstance(other, OverrideStateItem):
            return self.value == other.value
        return self.value == other

    def __gt__(self, other):
        """Defines behavior for the greater-than operator, >."""
        if isinstance(other, OverrideStateItem):
            return self.value > other.value
        return self.value > other

    def __lt__(self, other):
        """Defines behavior for the less-than operator, <."""
        if isinstance(other, OverrideStateItem):
            return self.value < other.value
        return self.value < other

    def __le__(self, other):
        """Defines behavior for the less-than-or-equal-to operator, <=."""
        if isinstance(other, OverrideStateItem):
            return self.value == other.value or self.value < other.value
        return self.value == other or self.value < other

    def __ge__(self, other):
        """Defines behavior for the greater-than-or-equal-to operator, >=."""
        if isinstance(other, OverrideStateItem):
            return self.value == other.value or self.value > other.value
        return self.value == other or self.value > other


class OverrideState:
    """Enumeration of override states.

    Each state should have unique value.
    """
    NOT_DEFINED = OverrideStateItem(-1, "Not defined")
    DEFAULTS = OverrideStateItem(0, "Defaults")
    STUDIO = OverrideStateItem(1, "Studio overrides")
    PROJECT = OverrideStateItem(2, "Project Overrides")
