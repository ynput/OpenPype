from Qt import QtCore

EXPANDER_WIDTH = 20


def flags(*args, **kwargs):
    type_name = kwargs.pop("type_name", "Flags")
    with_base = kwargs.pop("with_base", False)
    enums = {}
    for idx, attr_name in enumerate(args):
        if with_base:
            if idx == 0:
                enums[attr_name] = 0
                continue
            idx -= 1
        enums[attr_name] = 2**idx

    for attr_name, value in kwargs.items():
        enums[attr_name] = value
    return type(type_name, (), enums)


def roles(*args, **kwargs):
    type_name = kwargs.pop("type_name", "Roles")
    enums = {}
    for attr_name, value in kwargs.items():
        enums[attr_name] = value

    offset = 0
    for idx, attr_name in enumerate(args):
        _idx = idx + QtCore.Qt.UserRole + offset
        while _idx in enums.values():
            offset += 1
            _idx = idx + offset

        enums[attr_name] = _idx

    return type(type_name, (), enums)


Roles = roles(
    "ObjectIdRole",
    "ObjectUIdRole",
    "TypeRole",
    "PublishFlagsRole",
    "LogRecordsRole",

    "IsOptionalRole",
    "IsEnabledRole",

    "FamiliesRole",

    "DocstringRole",
    "PathModuleRole",
    "PluginActionsVisibleRole",
    "PluginValidActionsRole",
    "PluginActionProgressRole",

    "TerminalItemTypeRole",

    "IntentItemValue",

    type_name="ModelRoles"
)

InstanceStates = flags(
    "ContextType",
    "InProgress",
    "HasWarning",
    "HasError",
    "HasFinished",
    type_name="InstanceState"
)

PluginStates = flags(
    "IsCompatible",
    "InProgress",
    "WasProcessed",
    "WasSkipped",
    "HasWarning",
    "HasError",
    type_name="PluginState"
)

GroupStates = flags(
    "HasWarning",
    "HasError",
    "HasFinished",
    type_name="GroupStates"
)

PluginActionStates = flags(
    "InProgress",
    "HasFailed",
    "HasFinished",
    type_name="PluginActionStates"
)
