import copy
import collections

from .lib import (
    WRAPPER_TYPES,
    OverrideState,
    NOT_SET
)
from openpype.settings.constants import (
    METADATA_KEYS,
    M_OVERRIDEN_KEY,
    KEY_REGEX
)
from . import (
    BaseItemEntity,
    ItemEntity,
    BoolEntity,
    GUIEntity
)
from .exceptions import (
    SchemaDuplicatedKeys,
    EntitySchemaError,
    InvalidKeySymbols
)


example_schema = {
    "type": "dict-conditional",
    "key": "KEY",
    "label": "LABEL",
    "enum_key": "type",
    "enum_label": "label",
    "enum_children": [
        {
            "key": "action",
            "label": "Action",
            "children": [
                {
                    "type": "text",
                    "key": "key",
                    "label": "Key"
                },
                {
                    "type": "text",
                    "key": "label",
                    "label": "Label"
                },
                {
                    "type": "text",
                    "key": "command",
                    "label": "Comand"
                }
            ]
        },
        {
            "key": "menu",
            "label": "Menu",
            "children": [
                {
                    "type": "list",
                    "object_type": "text"
                }
            ]
        },
        {
            "key": "separator",
            "label": "Separator"
        }
    ]
}


class DictConditionalEntity(ItemEntity):
    schema_types = ["dict-conditional"]
    _default_label_wrap = {
        "use_label_wrap": False,
        "collapsible": False,
        "collapsed": True
    }

    def _item_initalization(self):
        self._default_metadata = NOT_SET
        self._studio_override_metadata = NOT_SET
        self._project_override_metadata = NOT_SET

        self._ignore_child_changes = False

        # `current_metadata` are still when schema is loaded
        # - only metadata stored with dict item are gorup overrides in
        #   M_OVERRIDEN_KEY
        self._current_metadata = {}
        self._metadata_are_modified = False

        # Children are stored by key as keys are immutable and are defined by
        # schema
        self.valid_value_types = (dict, )
        self.children = collections.defaultdict(list)
        self.non_gui_children = collections.defaultdict(dict)
        self.gui_layout = collections.defaultdict(list)

        if self.is_dynamic_item:
            self.require_key = False

        self.enum_key = self.schema_data.get("enum_key")
        self.enum_label = self.schema_data.get("enum_label")
        self.enum_children = self.schema_data.get("enum_children")

        self.enum_entity = None
        self.current_enum = None
