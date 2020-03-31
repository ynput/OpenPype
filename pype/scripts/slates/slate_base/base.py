import os
import re
import logging
import copy
import json
from uuid import uuid4


def load_default_style():
    cur_folder = os.path.dirname(os.path.abspath(__file__))
    default_json_path = os.path.join(cur_folder, "default_style.json")
    with open(default_json_path, "r") as _file:
        data = _file.read()
    return json.loads(data)


class BaseObj:
    """Base Object for slates."""

    obj_type = None
    available_parents = []
    all_style_keys = [
        "font-family", "font-size", "font-color", "font-bold", "font-italic",
        "bg-color", "bg-alter-color",
        "alignment-horizontal", "alignment-vertical",
        "padding", "padding-left", "padding-right",
        "padding-top", "padding-bottom",
        "margin", "margin-left", "margin-right",
        "margin-top", "margin-bottom", "width", "height",
        "fill", "word-wrap", "ellide", "max-lines"
    ]
    fill_data_regex = r"{[^}]+}"

    def __init__(self, parent, style={}, name=None, pos_x=None, pos_y=None):
        if not self.obj_type:
            raise NotImplementedError(
                "Class don't have set object type <{}>".format(
                    self.__class__.__name__
                )
            )

        parent_obj_type = None
        if parent:
            parent_obj_type = parent.obj_type

        if parent_obj_type not in self.available_parents:
            expected_parents = ", ".join(self.available_parents)
            raise Exception((
                "Invalid parent <{}> for <{}>. Expected <{}>"
            ).format(
                parent.__class__.__name__, self.obj_type, expected_parents
            ))

        self.parent = parent
        self._style = style

        self.id = uuid4()
        self.name = name
        self.items = {}

        self._pos_x = pos_x or 0
        self._pos_y = pos_y or 0

        log_parts = []
        module = self.__class__.__module__
        if module and module != "__main__":
            log_parts.append(module)
        log_parts.append(self.__class__.__name__)
        self.log = logging.getLogger(".".join(log_parts))

        if parent:
            parent.add_item(self)

    def fill_data_format(self):
        return

    @property
    def fill_data(self):
        return self.parent.fill_data

    @property
    def main_style(self):
        return load_default_style()

    def height(self):
        raise NotImplementedError(
            "Attribute `height` is not implemented for <{}>".format(
                self.__clas__.__name__
            )
        )

    def width(self):
        raise NotImplementedError(
            "Attribute `width` is not implemented for <{}>".format(
                self.__clas__.__name__
            )
        )

    def collect_data(self):
        return None

    def find_item(self, obj_type=None, name=None):
        obj_type_fits = False
        name_fits = False
        if obj_type is None or self.obj_type == obj_type:
            obj_type_fits = True

        if name is None or self.name != name:
            name_fits = True

        output = []
        if obj_type_fits and name_fits:
            output.append(self)

        if not self.items:
            return output

        for item in self.items.values():
            output.extend(
                item.find_item(obj_type=obj_type, name=name)
            )
        return output

    @property
    def full_style(self):
        if self.parent is not None:
            style = dict(val for val in self.parent.full_style.items())
        else:
            style = self.main_style

        for key, value in self._style.items():
            if key in self.all_style_keys:
                # TODO which variant is right?
                style[self.obj_type][key] = value
                # style["*"][key] = value
            else:
                if key not in style:
                    style[key] = {}

                if isinstance(style[key], dict):
                    style[key].update(value)
                else:
                    style[key] = value

        return style

    def get_style_for_obj_type(self, obj_type, style=None):
        if not style:
            style = copy.deepcopy(self.full_style)

        base = style.get("*") or {}
        obj_specific = style.get(obj_type) or {}
        name_specific = {}
        if self.name:
            name = str(self.name)
            if not name.startswith("#"):
                name = "#" + name
            name_specific = style.get(name) or {}

        if obj_type == "table-item":
            col_regex = r"table-item-col\[([\d\-, ]+)*\]"
            row_regex = r"table-item-row\[([\d\-, ]+)*\]"
            field_regex = (
                r"table-item-field\[(([ ]+)?\d+([ ]+)?:([ ]+)?\d+([ ]+)?)*\]"
            )
            # STRICT field regex (not allowed spaces)
            # fild_regex = r"table-item-field\[(\d+:\d+)*\]"

            def get_indexes_from_regex_match(result, field=False):
                group = result.group(1)
                indexes = []
                if field:
                    return [
                        int(part.strip()) for part in group.strip().split(":")
                    ]

                parts = group.strip().split(",")
                for part in parts:
                    part = part.strip()
                    if "-" not in part:
                        indexes.append(int(part))
                        continue

                    sub_parts = [
                        int(sub.strip()) for sub in part.split("-")
                    ]
                    if len(sub_parts) != 2:
                        # TODO logging
                        self.log.warning("Invalid range '{}'".format(part))
                        continue

                    for idx in range(sub_parts[0], sub_parts[1]+1):
                        indexes.append(idx)
                return indexes

            for key, value in style.items():
                if not key.startswith(obj_type):
                    continue

                result = re.search(col_regex, key)
                if result:
                    indexes = get_indexes_from_regex_match(result)
                    if self.col_idx in indexes:
                        obj_specific.update(value)
                    continue

                result = re.search(row_regex, key)
                if result:
                    indexes = get_indexes_from_regex_match(result)
                    if self.row_idx in indexes:
                        obj_specific.update(value)
                    continue

                result = re.search(field_regex, key)
                if result:
                    row_idx, col_idx = get_indexes_from_regex_match(
                        result, True
                    )
                    if self.col_idx == col_idx and self.row_idx == row_idx:
                        obj_specific.update(value)

        output = {}
        output.update(base)
        output.update(obj_specific)
        output.update(name_specific)

        return output

    @property
    def style(self):
        return self.get_style_for_obj_type(self.obj_type)

    @property
    def item_pos_x(self):
        if self.parent.obj_type == "main_frame":
            return int(self._pos_x)
        return 0

    @property
    def item_pos_y(self):
        if self.parent.obj_type == "main_frame":
            return int(self._pos_y)
        return 0

    @property
    def content_pos_x(self):
        pos_x = self.item_pos_x
        margin = self.style["margin"]
        margin_left = self.style.get("margin-left") or margin

        pos_x += margin_left

        return pos_x

    @property
    def content_pos_y(self):
        pos_y = self.item_pos_y
        margin = self.style["margin"]
        margin_top = self.style.get("margin-top") or margin
        return pos_y + margin_top

    @property
    def value_pos_x(self):
        pos_x = int(self.content_pos_x)
        padding = self.style["padding"]
        padding_left = self.style.get("padding-left")
        if padding_left is None:
            padding_left = padding

        pos_x += padding_left

        return pos_x

    @property
    def value_pos_y(self):
        pos_y = int(self.content_pos_y)
        padding = self.style["padding"]
        padding_top = self.style.get("padding-top")
        if padding_top is None:
            padding_top = padding

        pos_y += padding_top

        return pos_y

    @property
    def value_pos_start(self):
        return (self.value_pos_x, self.value_pos_y)

    @property
    def value_pos_end(self):
        pos_x, pos_y = self.value_pos_start
        pos_x += self.width()
        pos_y += self.height()
        return (pos_x, pos_y)

    @property
    def content_pos_start(self):
        return (self.content_pos_x, self.content_pos_y)

    @property
    def content_pos_end(self):
        pos_x, pos_y = self.content_pos_start
        pos_x += self.content_width()
        pos_y += self.content_height()
        return (pos_x, pos_y)

    def value_width(self):
        raise NotImplementedError(
            "Attribute <content_width> is not implemented <{}>".format(
                self.__class__.__name__
            )
        )

    def value_height(self):
        raise NotImplementedError(
            "Attribute <content_width> is not implemented for <{}>".format(
                self.__class__.__name__
            )
        )

    def content_width(self):
        width = self.value_width()
        padding = self.style["padding"]
        padding_left = self.style.get("padding-left")
        if padding_left is None:
            padding_left = padding

        padding_right = self.style.get("padding-right")
        if padding_right is None:
            padding_right = padding

        return width + padding_left + padding_right

    def content_height(self):
        height = self.value_height()
        padding = self.style["padding"]
        padding_top = self.style.get("padding-top")
        if padding_top is None:
            padding_top = padding

        padding_bottom = self.style.get("padding-bottom")
        if padding_bottom is None:
            padding_bottom = padding

        return height + padding_top + padding_bottom

    def width(self):
        width = self.content_width()

        margin = self.style["margin"]
        margin_left = self.style.get("margin-left") or margin
        margin_right = self.style.get("margin-right") or margin

        return width + margin_left + margin_right

    def height(self):
        height = self.content_height()

        margin = self.style["margin"]
        margin_top = self.style.get("margin-top") or margin
        margin_bottom = self.style.get("margin-bottom") or margin

        return height + margin_bottom + margin_top

    def add_item(self, item):
        self.items[item.id] = item
        item.fill_data_format()


    def reset(self):
        for item in self.items.values():
            item.reset()
