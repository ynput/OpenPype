import re
import collections
import uuid
from abc import ABCMeta, abstractmethod
import six


class AbstractAttrDefMeta(ABCMeta):
    """Meta class to validate existence of 'key' attribute.

    Each object of `AbtractAttrDef` mus have defined 'key' attribute.
    """
    def __call__(self, *args, **kwargs):
        obj = super(AbstractAttrDefMeta, self).__call__(*args, **kwargs)
        init_class = getattr(obj, "__init__class__", None)
        if init_class is not AbtractAttrDef:
            raise TypeError("{} super was not called in __init__.".format(
                type(obj)
            ))
        return obj


@six.add_metaclass(AbstractAttrDefMeta)
class AbtractAttrDef:
    """Abstraction of attribute definiton.

    Each attribute definition must have implemented validation and
    conversion method.

    Attribute definition should have ability to return "default" value. That
    can be based on passed data into `__init__` so is not abstracted to
    attribute.

    QUESTION:
    How to force to set `key` attribute?

    Args:
        key(str): Under which key will be attribute value stored.
        label(str): Attribute label.
        tooltip(str): Attribute tooltip.
        is_label_horizontal(bool): UI specific argument. Specify if label is
            next to value input or ahead.
    """
    is_value_def = True

    def __init__(
        self, key, default, label=None, tooltip=None, is_label_horizontal=None
    ):
        if is_label_horizontal is None:
            is_label_horizontal = True
        self.key = key
        self.label = label
        self.tooltip = tooltip
        self.default = default
        self.is_label_horizontal = is_label_horizontal
        self._id = uuid.uuid4()

        self.__init__class__ = AbtractAttrDef

    @property
    def id(self):
        return self._id

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return False
        return self.key == other.key

    @abstractmethod
    def convert_value(self, value):
        """Convert value to a valid one.

        Convert passed value to a valid type. Use default if value can't be
        converted.
        """
        pass


# -----------------------------------------
# UI attribute definitoins won't hold value
# -----------------------------------------

class UIDef(AbtractAttrDef):
    is_value_def = False

    def __init__(self, key=None, default=None, *args, **kwargs):
        super(UIDef, self).__init__(key, default, *args, **kwargs)

    def convert_value(self, value):
        return value


class UISeparatorDef(UIDef):
    pass


class UILabelDef(UIDef):
    def __init__(self, label):
        super(UILabelDef, self).__init__(label=label)


# ---------------------------------------
# Attribute defintioins should hold value
# ---------------------------------------

class UnknownDef(AbtractAttrDef):
    """Definition is not known because definition is not available.

    This attribute can be used to keep existing data unchanged but does not
    have known definition of type.
    """
    def __init__(self, key, default=None, **kwargs):
        kwargs["default"] = default
        super(UnknownDef, self).__init__(key, **kwargs)

    def convert_value(self, value):
        return value


class NumberDef(AbtractAttrDef):
    """Number definition.

    Number can have defined minimum/maximum value and decimal points. Value
    is integer if decimals are 0.

    Args:
        minimum(int, float): Minimum possible value.
        maximum(int, float): Maximum possible value.
        decimals(int): Maximum decimal points of value.
        default(int, float): Default value for conversion.
    """

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


class TextDef(AbtractAttrDef):
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


class EnumDef(AbtractAttrDef):
    """Enumeration of single item from items.

    Args:
        items: Items definition that can be coverted to
            `collections.OrderedDict`. Dictionary represent {value: label}
            relation.
        default: Default value. Must be one key(value) from passed items.
    """

    def __init__(self, key, items, default=None, **kwargs):
        if not items:
            raise ValueError((
                "Empty 'items' value. {} must have"
                " defined values on initialization."
            ).format(self.__class__.__name__))

        items = collections.OrderedDict(items)
        if default not in items:
            for _key in items.keys():
                default = _key
                break

        super(EnumDef, self).__init__(key, default=default, **kwargs)

        self.items = items

    def __eq__(self, other):
        if not super(EnumDef, self).__eq__(other):
            return False

        if set(self.items.keys()) != set(other.items.keys()):
            return False

        for key, label in self.items.items():
            if other.items[key] != label:
                return False
        return True

    def convert_value(self, value):
        if value in self.items:
            return value
        return self.default


class BoolDef(AbtractAttrDef):
    """Boolean representation.

    Args:
        default(bool): Default value. Set to `False` if not defined.
    """

    def __init__(self, key, default=None, **kwargs):
        if default is None:
            default = False
        super(BoolDef, self).__init__(key, default=default, **kwargs)

    def convert_value(self, value):
        if isinstance(value, bool):
            return value
        return self.default


class FileDef(AbtractAttrDef):
    """File definition.
    It is possible to define filters of allowed file extensions and if supports
    folders.
    Args:
        multipath(bool): Allow multiple path.
        folders(bool): Allow folder paths.
        extensions(list<str>): Allow files with extensions. Empty list will
            allow all extensions and None will disable files completely.
        default(str, list<str>): Defautl value.
    """

    def __init__(
        self, key, multipath=False, folders=None, extensions=None,
        default=None, **kwargs
    ):
        if folders is None and extensions is None:
            folders = True
            extensions = []

        if default is None:
            if multipath:
                default = []
            else:
                default = ""
        else:
            if multipath:
                if not isinstance(default, (tuple, list, set)):
                    raise TypeError((
                        "'default' argument must be 'list', 'tuple' or 'set'"
                        ", not '{}'"
                    ).format(type(default)))

            else:
                if not isinstance(default, six.string_types):
                    raise TypeError((
                        "'default' argument must be 'str' not '{}'"
                    ).format(type(default)))
                default = default.strip()

        # Change horizontal label
        is_label_horizontal = kwargs.get("is_label_horizontal")
        if is_label_horizontal is None:
            is_label_horizontal = True
            if multipath:
                is_label_horizontal = False
            kwargs["is_label_horizontal"] = is_label_horizontal

        self.multipath = multipath
        self.folders = folders
        self.extensions = extensions
        super(FileDef, self).__init__(key, default=default, **kwargs)

    def __eq__(self, other):
        if not super(FileDef, self).__eq__(other):
            return False

        return (
            self.multipath == other.multipath
            and self.folders == other.folders
            and self.extensions == other.extensions
        )

    def convert_value(self, value):
        if isinstance(value, six.string_types):
            if self.multipath:
                value = [value.strip()]
            else:
                value = value.strip()
            return value

        if isinstance(value, (tuple, list, set)):
            _value = []
            for item in value:
                if isinstance(item, six.string_types):
                    _value.append(item.strip())

            if self.multipath:
                return _value

            if not _value:
                return self.default
            return _value[0].strip()

        return str(value).strip()
