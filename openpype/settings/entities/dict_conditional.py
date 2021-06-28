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

        self._add_children()

    def _add_children(self):
        """Add children from schema data and repare enum items.

        Each enum item must have defined it's children. None are shared across
        all enum items.

        Nice to have: Have ability to have shared keys across all enum items.

        All children are stored by their enum item.
        """
        # Skip and wait for validation
        if not self.enum_children or not self.enum_key:
            return

        enum_items = []
        valid_enum_items = []
        for item in self.enum_children:
            if isinstance(item, dict) and "key" in item:
                valid_enum_items.append(item)

        first_key = None
        for item in valid_enum_items:
            item_key = item["key"]
            if first_key is None:
                first_key = item_key
            item_label = item.get("label") or item_key
            enum_items.append({item_key: item_label})

        if not enum_items:
            return

        self.current_enum = first_key

        enum_key = self.enum_key or "invalid"
        enum_schema = {
            "type": "enum",
            "multiselection": False,
            "enum_items": enum_items,
            "key": enum_key,
            "label": self.enum_label or enum_key
        }
        enum_entity = self.create_schema_object(enum_schema, self)
        self.enum_entity = enum_entity

        for item in valid_enum_items:
            item_key = item["key"]
            children = item.get("children") or []
            for children_schema in children:
                child_obj = self.create_schema_object(children_schema, self)
                self.children[item_key].append(child_obj)
                self.gui_layout[item_key].append(child_obj)
                if isinstance(child_obj, GUIEntity):
                    continue

                self.non_gui_children[item_key][child_obj.key] = child_obj
