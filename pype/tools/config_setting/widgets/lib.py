import uuid


class CustomNone:
    """Created object can be used as custom None (not equal to None).

    WARNING: Multiple created objects are not equal either.
    Exmple:
        >>> a = CustomNone()
        >>> a == None
        False
        >>> b = CustomNone()
        >>> a == b
        False
        >>> a == a
        True
    """

    def __init__(self):
        """Create uuid as identifier for custom None."""
        self.identifier = str(uuid.uuid4())

    def __bool__(self):
        """Return False (like default None)."""
        return False

    def __eq__(self, other):
        """Equality is compared by identifier value."""
        if type(other) == type(self):
            if other.identifier == self.identifier:
                return True
        return False

    def __str__(self):
        """Return value of identifier when converted to string."""
        return "<CustomNone-{}>".format(str(self.identifier))

    def __repr__(self):
        """Representation of custom None."""
        return "<CustomNone-{}>".format(str(self.identifier))


NOT_SET = CustomNone()
AS_WIDGET = type("AS_WIDGET", (), {})
METADATA_KEY = type("METADATA_KEY", (), {})


def convert_gui_data_to_overrides(data):
    pass


def convert_overrides_to_gui_data(data):
    pass
