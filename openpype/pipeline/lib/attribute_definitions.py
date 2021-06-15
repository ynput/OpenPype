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
