from .lib import STRING_TYPE
from .input_entities import InputEntity
from .exceptions import (
    BaseInvalidValue,
    InvalidValueType
)


class ColorEntity(InputEntity):
    schema_types = ["color"]

    def _item_initialization(self):
        self.valid_value_types = (list, )
        self.value_on_not_set = [0, 0, 0, 255]
        self.use_alpha = self.schema_data.get("use_alpha", True)

    def set_override_state(self, *args, **kwargs):
        super(ColorEntity, self).set_override_state(*args, **kwargs)
        value = self._current_value
        if (
            not self.use_alpha
            and isinstance(value, list)
            and len(value) == 4
        ):
            value[3] = 255

    def convert_to_valid_type(self, value):
        """Conversion to valid type.

        Complexity of entity requires to override BaseEntity implementation.
        """
        # Convertion to valid value type `list`
        if isinstance(value, (set, tuple)):
            value = list(value)

        # Skip other validations if is not `list`
        if not isinstance(value, list):
            raise InvalidValueType(
                self.valid_value_types, type(value), self.path
            )

        # Allow list of len 3 (last aplha is set to max)
        if len(value) == 3:
            value.append(255)

        if len(value) != 4:
            reason = "Color entity expect 4 items in list got {}".format(
                len(value)
            )
            raise BaseInvalidValue(reason, self.path)

        new_value = []
        for item in value:
            if not isinstance(item, int):
                if isinstance(item, (STRING_TYPE, float)):
                    item = int(item)

            is_valid = isinstance(item, int) and -1 < item < 256
            if not is_valid:
                reason = (
                    "Color entity expect 4 integers in range 0-255 got {}"
                ).format(value)
                raise BaseInvalidValue(reason, self.path)
            new_value.append(item)

        # Make sure
        if not self.use_alpha:
            new_value[3] = 255
        return new_value
