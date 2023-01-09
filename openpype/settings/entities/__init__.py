"""OpenPype Settings

Settings define how openpype and it's modules behave. They became main
component of dynamism.

OpenPype settings (ATM) have 3 layers:
1.) Defaults - defined in code
2.) Studio overrides - values that are applied on default that may modify only
    some values or None, result can be called "studio settings"
3.) Project overrides - values that are applied on studio settings, may modify
    some values or None and may modify values that are not modified in studio
    overrides

To be able do these overrides it is required to store metadata defying which
data are applied and how. Because of that it is not possible to modify
overrides manually and expect it would work right.

Structure of settings is defined with schemas. Schemas have defined structure
and possible types with possible attributes (Schemas and their description
can be found in "./schemas/README.md").

To modify settings it's recommended to use UI settings tool which can easily
visuallise how values are applied.

With help of setting entities it is possible to modify settings from code.

OpenPype has (ATM) 2 types of settings:
1.) System settings - global system settings, don't have project overrides
2.) Project settings - project specific settings

Startpoint is root entity that cares about access to other setting entities
in their scope. To be able work with entities it is required to understand
setting schemas and their structure. It is possible to work with dictionary
and list entities as with standard python objects.

```python
# Create an object of system settings.
system_settings = SystemSettings()

# How to get value of entity
print(system_settings["general"]["studio_name"].value)

>>> TestStudio Name

# How to set value
# Variant 1
system_settings["general"]["studio_name"] = "StudioidutS"
# Variant 2
system_settings["general"]["studio_name"].set("StudioidutS")

print(system_settings["general"]["studio_name"].value)
>>> StudioidutS
```
"""

from .exceptions import (
    SchemaError,
    DefaultsNotDefined,
    StudioDefaultsNotDefined,
    BaseInvalidValue,
    InvalidValueType,
    InvalidKeySymbols,
    SchemaMissingFileInfo,
    SchemeGroupHierarchyBug,
    SchemaDuplicatedKeys,
    SchemaDuplicatedEnvGroupKeys,
    SchemaTemplateMissingKeys
)
from .lib import (
    NOT_SET,
    OverrideState
)
from .base_entity import (
    BaseEntity,
    GUIEntity,
    BaseItemEntity,
    ItemEntity
)

from .root_entities import (
    SystemSettings,
    ProjectSettings
)

from .item_entities import (
    PathEntity,
    ListStrictEntity
)

from .input_entities import (
    EndpointEntity,
    InputEntity,

    NumberEntity,
    BoolEntity,
    TextEntity,
    PathInput,
    RawJsonEntity
)
from .color_entity import ColorEntity
from .enum_entity import (
    BaseEnumEntity,
    EnumEntity,
    HostsEnumEntity,
    AppsEnumEntity,
    ToolsEnumEntity,
    TaskTypeEnumEntity,
    DeadlineUrlEnumEntity,
    AnatomyTemplatesEnumEntity,
    ShotgridUrlEnumEntity
)

from .list_entity import ListEntity
from .dict_immutable_keys_entity import (
    DictImmutableKeysEntity,
    RootsDictEntity,
    SyncServerSites
)
from .dict_mutable_keys_entity import DictMutableKeysEntity
from .dict_conditional import (
    DictConditionalEntity,
    SyncServerProviders
)

from .anatomy_entities import AnatomyEntity
from .op_version_entity import (
    ProductionVersionsInputEntity,
    StagingVersionsInputEntity
)

__all__ = (
    "DefaultsNotDefined",
    "StudioDefaultsNotDefined",
    "BaseInvalidValue",
    "InvalidValueType",
    "InvalidKeySymbols",
    "SchemaMissingFileInfo",
    "SchemeGroupHierarchyBug",
    "SchemaDuplicatedKeys",
    "SchemaDuplicatedEnvGroupKeys",
    "SchemaTemplateMissingKeys",

    "NOT_SET",
    "OverrideState",

    "BaseEntity",
    "GUIEntity",
    "BaseItemEntity",
    "ItemEntity",

    "SystemSettings",
    "ProjectSettings",

    "PathEntity",
    "ListStrictEntity",

    "EndpointEntity",
    "InputEntity",

    "NumberEntity",
    "BoolEntity",
    "TextEntity",
    "PathInput",
    "RawJsonEntity",

    "ColorEntity",

    "BaseEnumEntity",
    "EnumEntity",
    "HostsEnumEntity",
    "AppsEnumEntity",
    "ToolsEnumEntity",
    "TaskTypeEnumEntity",
    "DeadlineUrlEnumEntity",
    "ShotgridUrlEnumEntity",
    "AnatomyTemplatesEnumEntity",

    "ListEntity",

    "DictImmutableKeysEntity",
    "RootsDictEntity",
    "SyncServerSites",

    "DictMutableKeysEntity",

    "DictConditionalEntity",
    "SyncServerProviders",

    "AnatomyEntity",

    "ProductionVersionsInputEntity",
    "StagingVersionsInputEntity"
)
