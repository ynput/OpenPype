from .input_entities import InputEntity
from .lib import NOT_SET


class EnumEntity(InputEntity):
    schema_types = ["enum"]

    def _item_initalization(self):
        self.multiselection = self.schema_data.get("multiselection", False)
        self.enum_items = self.schema_data["enum_items"]
        if not self.enum_items:
            raise ValueError("Attribute `enum_items` is not defined.")

        valid_keys = set()
        for item in self.enum_items:
            valid_keys.add(tuple(item.keys())[0])

        self.valid_keys = valid_keys

        if self.multiselection:
            self.valid_value_types = (list, )
            self.value_on_not_set = []
        else:
            valid_value_types = set()
            for key in valid_keys:
                if self.value_on_not_set is NOT_SET:
                    self.value_on_not_set = key
                valid_value_types.add(type(key))

            self.valid_value_types = tuple(valid_value_types)

        # GUI attribute
        self.placeholder = self.schema_data.get("placeholder")

    def schema_validations(self):
        enum_keys = set()
        for item in self.enum_items:
            key = tuple(item.keys())[0]
            if key in enum_keys:
                raise ValueError(
                    "{}: Key \"{}\" is more than once in enum items.".format(
                        self.path, key
                    )
                )
            enum_keys.add(key)

        super(EnumEntity, self).schema_validations()

    def set(self, value):
        if self.multiselection:
            if not isinstance(value, list):
                if isinstance(value, (set, tuple)):
                    value = list(value)
                else:
                    value = [value]
            check_values = value
        else:
            check_values = [value]

        self._validate_value_type(value)

        for item in check_values:
            if item not in self.valid_keys:
                raise ValueError(
                    "Invalid value \"{}\". Expected: {}".format(
                        item, self.valid_keys
                    )
                )
        self._current_value = value
        self._on_value_change()
