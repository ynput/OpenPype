import os
import re
import collections
import uuid
import json
import copy
from abc import ABCMeta, abstractmethod, abstractproperty

import six
import clique

# Global variable which store attribute definitions by type
#   - default types are registered on import
_attr_defs_by_type = {}


def register_attr_def_class(cls):
    """Register attribute definition.

    Currently are registered definitions used to deserialize data to objects.

    Attrs:
        cls (AbstractAttrDef): Non-abstract class to be registered with unique
            'type' attribute.

    Raises:
        KeyError: When type was already registered.
    """

    if cls.type in _attr_defs_by_type:
        raise KeyError("Type \"{}\" was already registered".format(cls.type))
    _attr_defs_by_type[cls.type] = cls


def get_attributes_keys(attribute_definitions):
    """Collect keys from list of attribute definitions.

    Args:
        attribute_definitions (List[AbstractAttrDef]): Objects of attribute
            definitions.

    Returns:
        Set[str]: Keys that will be created using passed attribute definitions.
    """

    keys = set()
    if not attribute_definitions:
        return keys

    for attribute_def in attribute_definitions:
        if not isinstance(attribute_def, UIDef):
            keys.add(attribute_def.key)
    return keys


def get_default_values(attribute_definitions):
    """Receive default values for attribute definitions.

    Args:
        attribute_definitions (List[AbstractAttrDef]): Attribute definitions
            for which default values should be collected.

    Returns:
        Dict[str, Any]: Default values for passet attribute definitions.
    """

    output = {}
    if not attribute_definitions:
        return output

    for attr_def in attribute_definitions:
        # Skip UI definitions
        if not isinstance(attr_def, UIDef):
            output[attr_def.key] = attr_def.default
    return output


class AbstractAttrDefMeta(ABCMeta):
    """Metaclass to validate existence of 'key' attribute.

    Each object of `AbstractAttrDef` mus have defined 'key' attribute.
    """

    def __call__(self, *args, **kwargs):
        obj = super(AbstractAttrDefMeta, self).__call__(*args, **kwargs)
        init_class = getattr(obj, "__init__class__", None)
        if init_class is not AbstractAttrDef:
            raise TypeError("{} super was not called in __init__.".format(
                type(obj)
            ))
        return obj


@six.add_metaclass(AbstractAttrDefMeta)
class AbstractAttrDef(object):
    """Abstraction of attribute definition.

    Each attribute definition must have implemented validation and
    conversion method.

    Attribute definition should have ability to return "default" value. That
    can be based on passed data into `__init__` so is not abstracted to
    attribute.

    QUESTION:
    How to force to set `key` attribute?

    Args:
        key (str): Under which key will be attribute value stored.
        default (Any): Default value of an attribute.
        label (str): Attribute label.
        tooltip (str): Attribute tooltip.
        is_label_horizontal (bool): UI specific argument. Specify if label is
            next to value input or ahead.
        hidden (bool): Will be item hidden (for UI purposes).
        disabled (bool): Item will be visible but disabled (for UI purposes).
    """

    type_attributes = []

    is_value_def = True

    def __init__(
        self,
        key,
        default,
        label=None,
        tooltip=None,
        is_label_horizontal=None,
        hidden=False,
        disabled=False
    ):
        if is_label_horizontal is None:
            is_label_horizontal = True

        if hidden is None:
            hidden = False

        self.key = key
        self.label = label
        self.tooltip = tooltip
        self.default = default
        self.is_label_horizontal = is_label_horizontal
        self.hidden = hidden
        self.disabled = disabled
        self._id = uuid.uuid4().hex

        self.__init__class__ = AbstractAttrDef

    @property
    def id(self):
        return self._id

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return False
        return (
            self.key == other.key
            and self.hidden == other.hidden
            and self.default == other.default
            and self.disabled == other.disabled
        )

    def __ne__(self, other):
        return not self.__eq__(other)

    @abstractproperty
    def type(self):
        """Attribute definition type also used as identifier of class.

        Returns:
            str: Type of attribute definition.
        """

        pass

    @abstractmethod
    def convert_value(self, value):
        """Convert value to a valid one.

        Convert passed value to a valid type. Use default if value can't be
        converted.
        """

        pass

    def serialize(self):
        """Serialize object to data so it's possible to recreate it.

        Returns:
            Dict[str, Any]: Serialized object that can be passed to
                'deserialize' method.
        """

        data = {
            "type": self.type,
            "key": self.key,
            "label": self.label,
            "tooltip": self.tooltip,
            "default": self.default,
            "is_label_horizontal": self.is_label_horizontal,
            "hidden": self.hidden,
            "disabled": self.disabled
        }
        for attr in self.type_attributes:
            data[attr] = getattr(self, attr)
        return data

    @classmethod
    def deserialize(cls, data):
        """Recreate object from data.

        Data can be received using 'serialize' method.
        """

        return cls(**data)


# -----------------------------------------
# UI attribute definitoins won't hold value
# -----------------------------------------

class UIDef(AbstractAttrDef):
    is_value_def = False

    def __init__(self, key=None, default=None, *args, **kwargs):
        super(UIDef, self).__init__(key, default, *args, **kwargs)

    def convert_value(self, value):
        return value


class UISeparatorDef(UIDef):
    type = "separator"


class UILabelDef(UIDef):
    type = "label"

    def __init__(self, label, key=None):
        super(UILabelDef, self).__init__(label=label, key=key)

    def __eq__(self, other):
        if not super(UILabelDef, self).__eq__(other):
            return False
        return self.label == other.label


# ---------------------------------------
# Attribute defintioins should hold value
# ---------------------------------------

class UnknownDef(AbstractAttrDef):
    """Definition is not known because definition is not available.

    This attribute can be used to keep existing data unchanged but does not
    have known definition of type.
    """

    type = "unknown"

    def __init__(self, key, default=None, **kwargs):
        kwargs["default"] = default
        super(UnknownDef, self).__init__(key, **kwargs)

    def convert_value(self, value):
        return value


class HiddenDef(AbstractAttrDef):
    """Hidden value of Any type.

    This attribute can be used for UI purposes to pass values related
    to other attributes (e.g. in multi-page UIs).

    Keep in mind the value should be possible to parse by json parser.
    """

    type = "hidden"

    def __init__(self, key, default=None, **kwargs):
        kwargs["default"] = default
        kwargs["hidden"] = True
        super(UnknownDef, self).__init__(key, **kwargs)

    def convert_value(self, value):
        return value


class NumberDef(AbstractAttrDef):
    """Number definition.

    Number can have defined minimum/maximum value and decimal points. Value
    is integer if decimals are 0.

    Args:
        minimum(int, float): Minimum possible value.
        maximum(int, float): Maximum possible value.
        decimals(int): Maximum decimal points of value.
        default(int, float): Default value for conversion.
    """

    type = "number"
    type_attributes = [
        "minimum",
        "maximum",
        "decimals"
    ]

    def __init__(
        self, key, minimum=None, maximum=None, decimals=None, default=None,
        **kwargs
    ):
        minimum = 0 if minimum is None else minimum
        maximum = 999999 if maximum is None else maximum
        # Swap min/max when are passed in opposited order
        if minimum > maximum:
            maximum, minimum = minimum, maximum

        if default is None:
            default = 0

        elif not isinstance(default, (int, float)):
            raise TypeError((
                "'default' argument must be 'int' or 'float', not '{}'"
            ).format(type(default)))

        # Fix default value by mim/max values
        if default < minimum:
            default = minimum

        elif default > maximum:
            default = maximum

        super(NumberDef, self).__init__(key, default=default, **kwargs)

        self.minimum = minimum
        self.maximum = maximum
        self.decimals = 0 if decimals is None else decimals

    def __eq__(self, other):
        if not super(NumberDef, self).__eq__(other):
            return False

        return (
            self.decimals == other.decimals
            and self.maximum == other.maximum
            and self.maximum == other.maximum
        )

    def convert_value(self, value):
        if isinstance(value, six.string_types):
            try:
                value = float(value)
            except Exception:
                pass

        if not isinstance(value, (int, float)):
            return self.default

        if self.decimals == 0:
            return int(value)
        return round(float(value), self.decimals)


class TextDef(AbstractAttrDef):
    """Text definition.

    Text can have multiline option so endline characters are allowed regex
    validation can be applied placeholder for UI purposes and default value.

    Regex validation is not part of attribute implemntentation.

    Args:
        multiline(bool): Text has single or multiline support.
        regex(str, re.Pattern): Regex validation.
        placeholder(str): UI placeholder for attribute.
        default(str, None): Default value. Empty string used when not defined.
    """

    type = "text"
    type_attributes = [
        "multiline",
        "placeholder",
    ]

    def __init__(
        self, key, multiline=None, regex=None, placeholder=None, default=None,
        **kwargs
    ):
        if default is None:
            default = ""

        super(TextDef, self).__init__(key, default=default, **kwargs)

        if multiline is None:
            multiline = False

        elif not isinstance(default, six.string_types):
            raise TypeError((
                "'default' argument must be a {}, not '{}'"
            ).format(six.string_types, type(default)))

        if isinstance(regex, six.string_types):
            regex = re.compile(regex)

        self.multiline = multiline
        self.placeholder = placeholder
        self.regex = regex

    def __eq__(self, other):
        if not super(TextDef, self).__eq__(other):
            return False

        return (
            self.multiline == other.multiline
            and self.regex == other.regex
        )

    def convert_value(self, value):
        if isinstance(value, six.string_types):
            return value
        return self.default

    def serialize(self):
        data = super(TextDef, self).serialize()
        data["regex"] = self.regex.pattern
        return data


class EnumDef(AbstractAttrDef):
    """Enumeration of items.

    Enumeration of single item from items. Or list of items if multiselection
    is enabled.

    Args:
        items (Union[list[str], list[dict[str, Any]]): Items definition that
            can be converted using 'prepare_enum_items'.
        default (Optional[Any]): Default value. Must be one key(value) from
            passed items or list of values for multiselection.
        multiselection (Optional[bool]): If True, multiselection is allowed.
            Output is list of selected items.
    """

    type = "enum"

    def __init__(
        self, key, items, default=None, multiselection=False, **kwargs
    ):
        if not items:
            raise ValueError((
                "Empty 'items' value. {} must have"
                " defined values on initialization."
            ).format(self.__class__.__name__))

        items = self.prepare_enum_items(items)
        item_values = [item["value"] for item in items]
        item_values_set = set(item_values)
        if multiselection:
            if default is None:
                default = []
            default = list(item_values_set.intersection(default))

        elif default not in item_values:
            default = next(iter(item_values), None)

        super(EnumDef, self).__init__(key, default=default, **kwargs)

        self.items = items
        self._item_values = item_values_set
        self.multiselection = multiselection

    def __eq__(self, other):
        if not super(EnumDef, self).__eq__(other):
            return False

        return (
            self.items == other.items
            and self.multiselection == other.multiselection
        )

    def convert_value(self, value):
        if not self.multiselection:
            if value in self._item_values:
                return value
            return self.default

        if value is None:
            return copy.deepcopy(self.default)
        return list(self._item_values.intersection(value))

    def serialize(self):
        data = super(EnumDef, self).serialize()
        data["items"] = copy.deepcopy(self.items)
        data["multiselection"] = self.multiselection
        return data

    @staticmethod
    def prepare_enum_items(items):
        """Convert items to unified structure.

        Output is a list where each item is dictionary with 'value'
        and 'label'.

        ```python
        # Example output
        [
            {"label": "Option 1", "value": 1},
            {"label": "Option 2", "value": 2},
            {"label": "Option 3", "value": 3}
        ]
        ```

        Args:
            items (Union[Dict[str, Any], List[Any], List[Dict[str, Any]]): The
                items to convert.

        Returns:
            List[Dict[str, Any]]: Unified structure of items.
        """

        output = []
        if isinstance(items, dict):
            for value, label in items.items():
                output.append({"label": label, "value": value})

        elif isinstance(items, (tuple, list, set)):
            for item in items:
                if isinstance(item, dict):
                    # Validate if 'value' is available
                    if "value" not in item:
                        raise KeyError("Item does not contain 'value' key.")

                    if "label" not in item:
                        item["label"] = str(item["value"])
                elif isinstance(item, (list, tuple)):
                    if len(item) == 2:
                        value, label = item
                    elif len(item) == 1:
                        value = item[0]
                        label = str(value)
                    else:
                        raise ValueError((
                            "Invalid items count {}."
                            " Expected 1 or 2. Value: {}"
                        ).format(len(item), str(item)))

                    item = {"label": label, "value": value}
                else:
                    item = {"label": str(item), "value": item}
                output.append(item)

        else:
            raise TypeError(
                "Unknown type for enum items '{}'".format(type(items))
            )

        return output


class BoolDef(AbstractAttrDef):
    """Boolean representation.

    Args:
        default(bool): Default value. Set to `False` if not defined.
    """

    type = "bool"

    def __init__(self, key, default=None, **kwargs):
        if default is None:
            default = False
        super(BoolDef, self).__init__(key, default=default, **kwargs)

    def convert_value(self, value):
        if isinstance(value, bool):
            return value
        return self.default


class FileDefItem(object):
    def __init__(
        self, directory, filenames, frames=None, template=None
    ):
        self.directory = directory

        self.filenames = []
        self.is_sequence = False
        self.template = None
        self.frames = []
        self.is_empty = True

        self.set_filenames(filenames, frames, template)

    def __str__(self):
        return json.dumps(self.to_dict())

    def __repr__(self):
        if self.is_empty:
            filename = "< empty >"
        elif self.is_sequence:
            filename = self.template
        else:
            filename = self.filenames[0]

        return "<{}: \"{}\">".format(
            self.__class__.__name__,
            os.path.join(self.directory, filename)
        )

    @property
    def label(self):
        if self.is_empty:
            return None

        if not self.is_sequence:
            return self.filenames[0]

        frame_start = self.frames[0]
        filename_template = os.path.basename(self.template)
        if len(self.frames) == 1:
            return "{} [{}]".format(filename_template, frame_start)

        frame_end = self.frames[-1]
        expected_len = (frame_end - frame_start) + 1
        if expected_len == len(self.frames):
            return "{} [{}-{}]".format(
                filename_template, frame_start, frame_end
            )

        ranges = []
        _frame_start = None
        _frame_end = None
        for frame in range(frame_start, frame_end + 1):
            if frame not in self.frames:
                add_to_ranges = _frame_start is not None
            elif _frame_start is None:
                _frame_start = _frame_end = frame
                add_to_ranges = frame == frame_end
            else:
                _frame_end = frame
                add_to_ranges = frame == frame_end

            if add_to_ranges:
                if _frame_start != _frame_end:
                    _range = "{}-{}".format(_frame_start, _frame_end)
                else:
                    _range = str(_frame_start)
                ranges.append(_range)
                _frame_start = _frame_end = None
        return "{} [{}]".format(
            filename_template, ",".join(ranges)
        )

    def split_sequence(self):
        if not self.is_sequence:
            raise ValueError("Cannot split single file item")

        paths = [
            os.path.join(self.directory, filename)
            for filename in self.filenames
        ]
        return self.from_paths(paths, False)

    @property
    def ext(self):
        if self.is_empty:
            return None
        _, ext = os.path.splitext(self.filenames[0])
        if ext:
            return ext
        return None

    @property
    def lower_ext(self):
        ext = self.ext
        if ext is not None:
            return ext.lower()
        return ext

    @property
    def is_dir(self):
        if self.is_empty:
            return False

        # QUESTION a better way how to define folder (in init argument?)
        if self.ext:
            return False
        return True

    def set_directory(self, directory):
        self.directory = directory

    def set_filenames(self, filenames, frames=None, template=None):
        if frames is None:
            frames = []
        is_sequence = False
        if frames:
            is_sequence = True

        if is_sequence and not template:
            raise ValueError("Missing template for sequence")

        self.is_empty = len(filenames) == 0
        self.filenames = filenames
        self.template = template
        self.frames = frames
        self.is_sequence = is_sequence

    @classmethod
    def create_empty_item(cls):
        return cls("", "")

    @classmethod
    def from_value(cls, value, allow_sequences):
        """Convert passed value to FileDefItem objects.

        Returns:
            list: Created FileDefItem objects.
        """

        # Convert single item to iterable
        if not isinstance(value, (list, tuple, set)):
            value = [value]

        output = []
        str_filepaths = []
        for item in value:
            if isinstance(item, dict):
                item = cls.from_dict(item)

            if isinstance(item, FileDefItem):
                if not allow_sequences and item.is_sequence:
                    output.extend(item.split_sequence())
                else:
                    output.append(item)

            elif isinstance(item, six.string_types):
                str_filepaths.append(item)
            else:
                raise TypeError(
                    "Unknown type \"{}\". Can't convert to {}".format(
                        str(type(item)), cls.__name__
                    )
                )

        if str_filepaths:
            output.extend(cls.from_paths(str_filepaths, allow_sequences))

        return output

    @classmethod
    def from_dict(cls, data):
        return cls(
            data["directory"],
            data["filenames"],
            data.get("frames"),
            data.get("template")
        )

    @classmethod
    def from_paths(cls, paths, allow_sequences):
        filenames_by_dir = collections.defaultdict(list)
        for path in paths:
            normalized = os.path.normpath(path)
            directory, filename = os.path.split(normalized)
            filenames_by_dir[directory].append(filename)

        output = []
        for directory, filenames in filenames_by_dir.items():
            if allow_sequences:
                cols, remainders = clique.assemble(filenames)
            else:
                cols = []
                remainders = filenames

            for remainder in remainders:
                output.append(cls(directory, [remainder]))

            for col in cols:
                frames = list(col.indexes)
                paths = [filename for filename in col]
                template = col.format("{head}{padding}{tail}")

                output.append(cls(
                    directory, paths, frames, template
                ))

        return output

    def to_dict(self):
        output = {
            "is_sequence": self.is_sequence,
            "directory": self.directory,
            "filenames": list(self.filenames),
        }
        if self.is_sequence:
            output.update({
                "template": self.template,
                "frames": list(sorted(self.frames)),
            })

        return output


class FileDef(AbstractAttrDef):
    """File definition.
    It is possible to define filters of allowed file extensions and if supports
    folders.
    Args:
        single_item(bool): Allow only single path item.
        folders(bool): Allow folder paths.
        extensions(List[str]): Allow files with extensions. Empty list will
            allow all extensions and None will disable files completely.
        extensions_label(str): Custom label shown instead of extensions in UI.
        default(str, List[str]): Default value.
    """

    type = "path"
    type_attributes = [
        "single_item",
        "folders",
        "extensions",
        "allow_sequences",
        "extensions_label",
    ]

    def __init__(
        self, key, single_item=True, folders=None, extensions=None,
        allow_sequences=True, extensions_label=None, default=None, **kwargs
    ):
        if folders is None and extensions is None:
            folders = True
            extensions = []

        if default is None:
            if single_item:
                default = FileDefItem.create_empty_item().to_dict()
            else:
                default = []
        else:
            if single_item:
                if isinstance(default, dict):
                    FileDefItem.from_dict(default)

                elif isinstance(default, six.string_types):
                    default = FileDefItem.from_paths([default.strip()])[0]

                else:
                    raise TypeError((
                        "'default' argument must be 'str' or 'dict' not '{}'"
                    ).format(type(default)))

            else:
                if not isinstance(default, (tuple, list, set)):
                    raise TypeError((
                        "'default' argument must be 'list', 'tuple' or 'set'"
                        ", not '{}'"
                    ).format(type(default)))

        # Change horizontal label
        is_label_horizontal = kwargs.get("is_label_horizontal")
        if is_label_horizontal is None:
            kwargs["is_label_horizontal"] = False

        self.single_item = single_item
        self.folders = folders
        self.extensions = set(extensions)
        self.allow_sequences = allow_sequences
        self.extensions_label = extensions_label
        super(FileDef, self).__init__(key, default=default, **kwargs)

    def __eq__(self, other):
        if not super(FileDef, self).__eq__(other):
            return False

        return (
            self.single_item == other.single_item
            and self.folders == other.folders
            and self.extensions == other.extensions
            and self.allow_sequences == other.allow_sequences
        )

    def convert_value(self, value):
        if isinstance(value, six.string_types) or isinstance(value, dict):
            value = [value]

        if isinstance(value, (tuple, list, set)):
            string_paths = []
            dict_items = []
            for item in value:
                if isinstance(item, six.string_types):
                    string_paths.append(item.strip())
                elif isinstance(item, dict):
                    try:
                        FileDefItem.from_dict(item)
                        dict_items.append(item)
                    except (ValueError, KeyError):
                        pass

            if string_paths:
                file_items = FileDefItem.from_paths(string_paths)
                dict_items.extend([
                    file_item.to_dict()
                    for file_item in file_items
                ])

            if not self.single_item:
                return dict_items

            if not dict_items:
                return self.default
            return dict_items[0]

        if self.single_item:
            return FileDefItem.create_empty_item().to_dict()
        return []


def serialize_attr_def(attr_def):
    """Serialize attribute definition to data.

    Args:
        attr_def (AbstractAttrDef): Attribute definition to serialize.

    Returns:
        Dict[str, Any]: Serialized data.
    """

    return attr_def.serialize()


def serialize_attr_defs(attr_defs):
    """Serialize attribute definitions to data.

    Args:
        attr_defs (List[AbstractAttrDef]): Attribute definitions to serialize.

    Returns:
        List[Dict[str, Any]]: Serialized data.
    """

    return [
        serialize_attr_def(attr_def)
        for attr_def in attr_defs
    ]


def deserialize_attr_def(attr_def_data):
    """Deserialize attribute definition from data.

    Args:
        attr_def (Dict[str, Any]): Attribute definition data to deserialize.
    """

    attr_type = attr_def_data.pop("type")
    cls = _attr_defs_by_type[attr_type]
    return cls.deserialize(attr_def_data)


def deserialize_attr_defs(attr_defs_data):
    """Deserialize attribute definitions.

    Args:
        List[Dict[str, Any]]: List of attribute definitions.
    """

    return [
        deserialize_attr_def(attr_def_data)
        for attr_def_data in attr_defs_data
    ]


# Register attribute definitions
for _attr_class in (
    UISeparatorDef,
    UILabelDef,
    UnknownDef,
    NumberDef,
    TextDef,
    EnumDef,
    BoolDef,
    FileDef
):
    register_attr_def_class(_attr_class)
