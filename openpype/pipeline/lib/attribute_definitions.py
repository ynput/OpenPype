from abc import ABCMeta, abstractmethod
import six


@six.add_metaclass(ABCMeta)
class AbtractAttrDef:
    """Abstraction of attribute definiton.

    Each attribute definition must have implemented validation and
    conversion method.

    Attribute definition should have ability to return "default" value. That
    can be based on passed data into `__init__` so is not abstracted to
    attribute.
    """

    @abstractmethod
    def convert_value(self, value):
        """Convert value to a valid one.

        Convert passed value to a valid type. Use default if value can't be
        converted.
        """
        pass


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
        self, minimum=None, maximum=None, decimals=None, default=None
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

        self.minimum = minimum
        self.maximum = maximum
        self.default = default
        self.decimals = 0 if decimals is None else decimals

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
class BoolDef(AbtractAttrDef):
    """Boolean representation.

    Args:
        default(bool): Default value. Set to `False` if not defined.
    """

    def __init__(self, default=None):
        if default is None:
            default = False
        self.default = default

    def convert_value(self, value):
        if isinstance(value, bool):
            return value
        return self.default
