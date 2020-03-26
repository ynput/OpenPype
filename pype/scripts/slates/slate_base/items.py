import os
import re
from PIL import Image

from .base import BaseObj
from .font_factory import FontFactory


class BaseItem(BaseObj):
    available_parents = ["main_frame", "layer"]

    @property
    def item_pos_x(self):
        if self.parent.obj_type == "main_frame":
            return self._pos_x
        return self.parent.child_pos_x(self.id)

    @property
    def item_pos_y(self):
        if self.parent.obj_type == "main_frame":
            return self._pos_y
        return self.parent.child_pos_y(self.id)

    def add_item(self, *args, **kwargs):
        raise Exception("Can't add item to an item, use layers instead.")

    def draw(self, image, drawer):
        raise NotImplementedError(
            "Method `draw` is not implemented for <{}>".format(
                self.__clas__.__name__
            )
        )


class ItemImage(BaseItem):
    obj_type = "image"

    def __init__(self, image_path, *args, **kwargs):
        self.image_path = image_path
        super(ItemImage, self).__init__(*args, **kwargs)

    def fill_data_format(self):
        if re.match(self.fill_data_regex, self.image_path):
            self.image_path = self.image_path.format(**self.fill_data)

    def draw(self, image, drawer):
        source_image = Image.open(os.path.normpath(self.image_path))
        paste_image = source_image.resize(
            (self.value_width(), self.value_height()),
            Image.ANTIALIAS
        )
        image.paste(
            paste_image,
            (self.value_pos_x, self.value_pos_y)
        )

    def value_width(self):
        return int(self.style["width"])

    def value_height(self):
        return int(self.style["height"])


class ItemRectangle(BaseItem):
    obj_type = "rectangle"

    def draw(self, image, drawer):
        bg_color = self.style["bg-color"]
        fill = self.style.get("fill", False)
        kwargs = {}
        if fill:
            kwargs["fill"] = bg_color
        else:
            kwargs["outline"] = bg_color

        start_pos_x = self.value_pos_x
        start_pos_y = self.value_pos_y
        end_pos_x = start_pos_x + self.value_width()
        end_pos_y = start_pos_y + self.value_height()
        drawer.rectangle(
            (
                (start_pos_x, start_pos_y),
                (end_pos_x, end_pos_y)
            ),
            **kwargs
        )

    def value_width(self):
        return int(self.style["width"])

    def value_height(self):
        return int(self.style["height"])


class ItemPlaceHolder(BaseItem):
    obj_type = "placeholder"

    def __init__(self, image_path, *args, **kwargs):
        self.image_path = image_path
        super(ItemPlaceHolder, self).__init__(*args, **kwargs)

    def fill_data_format(self):
        if re.match(self.fill_data_regex, self.image_path):
            self.image_path = self.image_path.format(**self.fill_data)

    def draw(self, image, drawer):
        bg_color = self.style["bg-color"]

        kwargs = {}
        if bg_color != "tranparent":
            kwargs["fill"] = bg_color

        start_pos_x = self.value_pos_x
        start_pos_y = self.value_pos_y
        end_pos_x = start_pos_x + self.value_width()
        end_pos_y = start_pos_y + self.value_height()

        drawer.rectangle(
            (
                (start_pos_x, start_pos_y),
                (end_pos_x, end_pos_y)
            ),
            **kwargs
        )

    def value_width(self):
        return int(self.style["width"])

    def value_height(self):
        return int(self.style["height"])

    def collect_data(self):
        return {
            "pos_x": self.value_pos_x,
            "pos_y": self.value_pos_y,
            "width": self.value_width(),
            "height": self.value_height(),
            "path": self.image_path
        }


class ItemText(BaseItem):
    obj_type = "text"

    def __init__(self, value, *args, **kwargs):
        self.value = value
        super(ItemText, self).__init__(*args, **kwargs)

    def draw(self, image, drawer):
        bg_color = self.style["bg-color"]
        if bg_color and bg_color.lower() != "transparent":
            # TODO border outline styles
            drawer.rectangle(
                (self.content_pos_start, self.content_pos_end),
                fill=bg_color,
                outline=None
            )

        font_color = self.style["font-color"]
        font_family = self.style["font-family"]
        font_size = self.style["font-size"]
        font_bold = self.style.get("font-bold", False)
        font_italic = self.style.get("font-italic", False)

        font = FontFactory.get_font(
            font_family, font_size, font_italic, font_bold
        )
        drawer.text(
            self.value_pos_start,
            self.value,
            font=font,
            fill=font_color
        )

    def value_width(self):
        font_family = self.style["font-family"]
        font_size = self.style["font-size"]
        font_bold = self.style.get("font-bold", False)
        font_italic = self.style.get("font-italic", False)

        font = FontFactory.get_font(
            font_family, font_size, font_italic, font_bold
        )
        width = font.getsize(self.value)[0]
        return int(width)

    def value_height(self):
        font_family = self.style["font-family"]
        font_size = self.style["font-size"]
        font_bold = self.style.get("font-bold", False)
        font_italic = self.style.get("font-italic", False)

        font = FontFactory.get_font(
            font_family, font_size, font_italic, font_bold
        )
        height = font.getsize(self.value)[1]
        return int(height)


class ItemTable(BaseItem):

    obj_type = "table"

    def __init__(self, values, use_alternate_color=False, *args, **kwargs):

        self.values_by_cords = None
        self.prepare_values(values)

        super(ItemTable, self).__init__(*args, **kwargs)
        self.size_values = None
        self.calculate_sizes()

        self.use_alternate_color = use_alternate_color

    def add_item(self, item):
        if item.obj_type == "table-item":
            return
        super(ItemTable, self).add_item(item)

    def fill_data_format(self):
        for item in self.values:
            item.fill_data_format()

    def prepare_values(self, _values):
        values = []
        values_by_cords = []
        row_count = 0
        col_count = 0
        for row in _values:
            row_count += 1
            if len(row) > col_count:
                col_count = len(row)

        for row_idx in range(row_count):
            values_by_cords.append([])
            for col_idx in range(col_count):
                values_by_cords[row_idx].append([])
                if col_idx <= len(_values[row_idx]) - 1:
                    col = _values[row_idx][col_idx]
                else:
                    col = ""

                col_item = TableField(row_idx, col_idx, col, parent=self)
                values_by_cords[row_idx][col_idx] = col_item
                values.append(col_item)

        self.values = values
        self.values_by_cords = values_by_cords

    def calculate_sizes(self):
        row_heights = []
        col_widths = []
        for row_idx, row in enumerate(self.values_by_cords):
            row_heights.append(0)
            for col_idx, col_item in enumerate(row):
                if len(col_widths) < col_idx + 1:
                    col_widths.append(0)

                _width = col_widths[col_idx]
                item_width = col_item.width()
                if _width < item_width:
                    col_widths[col_idx] = item_width

                _height = row_heights[row_idx]
                item_height = col_item.height()
                if _height < item_height:
                    row_heights[row_idx] = item_height

        self.size_values = (row_heights, col_widths)

    def draw(self, image, drawer):
        bg_color = self.style["bg-color"]
        if bg_color and bg_color.lower() != "transparent":
            # TODO border outline styles
            drawer.rectangle(
                (self.content_pos_start, self.content_pos_end),
                fill=bg_color,
                outline=None
            )

        for value in self.values:
            value.draw(image, drawer)

    def value_width(self):
        row_heights, col_widths = self.size_values
        width = 0
        for _width in col_widths:
            width += _width

        if width != 0:
            width -= 1
        return width

    def value_height(self):
        row_heights, col_widths = self.size_values
        height = 0
        for _height in row_heights:
            height += _height

        if height != 0:
            height -= 1
        return height

    def content_pos_info_by_cord(self, row_idx, col_idx):
        row_heights, col_widths = self.size_values
        pos_x = int(self.value_pos_x)
        pos_y = int(self.value_pos_y)
        width = 0
        height = 0
        for idx, value in enumerate(col_widths):
            if col_idx == idx:
                width = value
                break
            pos_x += value

        for idx, value in enumerate(row_heights):
            if row_idx == idx:
                height = value
                break
            pos_y += value

        return (pos_x, pos_y, width, height)


class TableField(BaseItem):

    obj_type = "table-item"
    available_parents = ["table"]
    ellide_text = "..."

    def __init__(self, row_idx, col_idx, value, *args, **kwargs):
        super(TableField, self).__init__(*args, **kwargs)
        self.row_idx = row_idx
        self.col_idx = col_idx
        self.value = value

    def recalculate_by_width(self, value, max_width):
        padding = self.style["padding"]
        padding_left = self.style.get("padding-left")
        if padding_left is None:
            padding_left = padding

        padding_right = self.style.get("padding-right")
        if padding_right is None:
            padding_right = padding

        max_width -= (padding_left + padding_right)

        if not value:
            return ""

        word_wrap = self.style.get("word-wrap")
        ellide = self.style.get("ellide")
        max_lines = self.style.get("max-lines")

        font_family = self.style["font-family"]
        font_size = self.style["font-size"]
        font_bold = self.style.get("font-bold", False)
        font_italic = self.style.get("font-italic", False)

        font = FontFactory.get_font(
            font_family, font_size, font_italic, font_bold
        )
        val_width = font.getsize(value)[0]
        if val_width <= max_width:
            return value

        if not ellide and not word_wrap:
            # TODO logging
            self.log.warning((
                "Can't draw text because is too long with"
                " `word-wrap` and `ellide` turned off <{}>"
            ).format(value))
            return ""

        elif ellide and not word_wrap:
            max_lines = 1

        words = [word for word in value.split()]
        words_len = len(words)
        lines = []
        last_index = None
        while True:
            start_index = 0
            if last_index is not None:
                start_index = int(last_index) + 1

            line = ""
            for idx in range(start_index, words_len):
                _word = words[idx]
                connector = " "
                if line == "":
                    connector = ""

                _line = connector.join([line, _word])
                _line_width = font.getsize(_line)[0]
                if _line_width > max_width:
                    break
                line = _line
                last_index = idx

            if line:
                lines.append(line)

            if last_index == words_len - 1:
                break

            elif last_index is None:
                add_message = ""
                if ellide:
                    add_message = " String was shortened to `{}`."
                    line = ""
                    for idx, char in enumerate(words[idx]):
                        _line = line + char + self.ellide_text
                        _line_width = font.getsize(_line)[0]
                        if _line_width > max_width:
                            if idx == 0:
                                line = _line
                            break
                        line = line + char

                    lines.append(line)
                # TODO logging
                self.log.warning((
                    "Font size is too big.{} <{}>"
                ).format(add_message, value))
                break

        output = ""
        if not lines:
            return output

        over_max_lines = (max_lines and len(lines) > max_lines)
        if not over_max_lines:
            return "\n".join([line for line in lines])

        lines = [lines[idx] for idx in range(max_lines)]
        if not ellide:
            return "\n".join(lines)

        last_line = lines[-1]
        last_line_width = font.getsize(last_line + self.ellide_text)[0]
        if last_line_width <= max_width:
            lines[-1] += self.ellide_text
            return "\n".join([line for line in lines])

        last_line_words = last_line.split()
        if len(last_line_words) == 1:
            if max_lines > 1:
                # TODO try previous line?
                lines[-1] = self.ellide_text
                return "\n".join([line for line in lines])

            line = ""
            for idx, word in enumerate(last_line_words):
                _line = line + word + self.ellide_text
                _line_width = font.getsize(_line)[0]
                if _line_width > max_width:
                    if idx == 0:
                        line = _line
                    break
                line = _line
            lines[-1] = line

            return "\n".join([line for line in lines])

        line = ""
        for idx, _word in enumerate(last_line_words):
            connector = " "
            if line == "":
                connector = ""

            _line = connector.join([line, _word + self.ellide_text])
            _line_width = font.getsize(_line)[0]

            if _line_width <= max_width:
                line = connector.join([line, _word])
                continue

            if idx != 0:
                line += self.ellide_text
                break

            if max_lines != 1:
                # TODO try previous line?
                line = self.ellide_text
                break

            for idx, char in enumerate(_word):
                _line = line + char + self.ellide_text
                _line_width = font.getsize(_line)[0]
                if _line_width > max_width:
                    if idx == 0:
                        line = _line
                    break
                line = line + char
            break

        lines[-1] = line

        return "\n".join([line for line in lines])

    def fill_data_format(self):
        value = self.value
        if re.match(self.fill_data_regex, value):
            value = value.format(**self.fill_data)

        self.orig_value = value

        max_width = self.style.get("max-width")
        max_width = self.style.get("width") or max_width
        if max_width:
            value = self.recalculate_by_width(value, max_width)

        self.value = value

    def content_width(self):
        width = self.style.get("width")
        if width:
            return int(width)
        return super(TableField, self).content_width()

    def content_height(self):
        return super(TableField, self).content_height()

    def value_width(self):
        if not self.value:
            return 0

        font_family = self.style["font-family"]
        font_size = self.style["font-size"]
        font_bold = self.style.get("font-bold", False)
        font_italic = self.style.get("font-italic", False)

        font = FontFactory.get_font(
            font_family, font_size, font_italic, font_bold
        )
        width = font.getsize_multiline(self.value)[0] + 1

        min_width = self.style.get("min-height")
        if min_width and min_width > width:
            width = min_width

        return int(width)

    def value_height(self):
        if not self.value:
            return 0

        height = self.style.get("height")
        if height:
            return int(height)

        font_family = self.style["font-family"]
        font_size = self.style["font-size"]
        font_bold = self.style.get("font-bold", False)
        font_italic = self.style.get("font-italic", False)

        font = FontFactory.get_font(
            font_family, font_size, font_italic, font_bold
        )
        height = font.getsize_multiline(self.value)[1] + 1

        min_height = self.style.get("min-height")
        if min_height and min_height > height:
            height = min_height

        return int(height)

    @property
    def item_pos_x(self):
        pos_x, pos_y, width, height = (
            self.parent.content_pos_info_by_cord(self.row_idx, self.col_idx)
        )
        return pos_x

    @property
    def item_pos_y(self):
        pos_x, pos_y, width, height = (
            self.parent.content_pos_info_by_cord(self.row_idx, self.col_idx)
        )
        return pos_y

    @property
    def value_pos_x(self):
        pos_x, pos_y, width, height = (
            self.parent.content_pos_info_by_cord(self.row_idx, self.col_idx)
        )
        alignment_hor = self.style["alignment-horizontal"].lower()
        if alignment_hor in ["center", "centre"]:
            pos_x += (width - self.value_width()) / 2

        elif alignment_hor == "right":
            pos_x += width - self.value_width()

        else:
            padding = self.style["padding"]
            padding_left = self.style.get("padding-left")
            if padding_left is None:
                padding_left = padding

            pos_x += padding_left

        return int(pos_x)

    @property
    def value_pos_y(self):
        pos_x, pos_y, width, height = (
            self.parent.content_pos_info_by_cord(self.row_idx, self.col_idx)
        )

        alignment_ver = self.style["alignment-vertical"].lower()
        if alignment_ver in ["center", "centre"]:
            pos_y += (height - self.value_height()) / 2

        elif alignment_ver == "bottom":
            pos_y += height - self.value_height()

        else:
            padding = self.style["padding"]
            padding_top = self.style.get("padding-top")
            if padding_top is None:
                padding_top = padding

            pos_y += padding_top

        return int(pos_y)

    def draw(self, image, drawer):
        pos_x, pos_y, width, height = (
            self.parent.content_pos_info_by_cord(self.row_idx, self.col_idx)
        )
        pos_start = (pos_x, pos_y)
        pos_end = (pos_x + width, pos_y + height)
        bg_color = self.style["bg-color"]
        if self.parent.use_alternate_color and (self.row_idx % 2) == 1:
            bg_color = self.style["bg-alter-color"]

        if bg_color and bg_color.lower() != "transparent":
            # TODO border outline styles
            drawer.rectangle(
                (pos_start, pos_end),
                fill=bg_color,
                outline=None
            )

        font_color = self.style["font-color"]
        font_family = self.style["font-family"]
        font_size = self.style["font-size"]
        font_bold = self.style.get("font-bold", False)
        font_italic = self.style.get("font-italic", False)

        font = FontFactory.get_font(
            font_family, font_size, font_italic, font_bold
        )

        alignment_hor = self.style["alignment-horizontal"].lower()
        if alignment_hor == "centre":
            alignment_hor = "center"

        drawer.multiline_text(
            self.value_pos_start,
            self.value,
            font=font,
            fill=font_color,
            align=alignment_hor
        )
