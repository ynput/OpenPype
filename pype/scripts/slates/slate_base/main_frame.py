import os
import re
from PIL import Image, ImageDraw

from .base import BaseObj


class MainFrame(BaseObj):

    obj_type = "main_frame"
    available_parents = [None]

    def __init__(
        self, width, height, destination_path, fill_data={}, *args, **kwargs
    ):
        kwargs["parent"] = None
        super(MainFrame, self).__init__(*args, **kwargs)
        self._width = width
        self._height = height
        self.dst_path = destination_path
        self._fill_data = fill_data
        self.fill_data_format()

    def fill_data_format(self):
        if re.match(self.fill_data_regex, self.dst_path):
            self.dst_path = self.dst_path.format(**self.fill_data)

    @property
    def fill_data(self):
        return self._fill_data

    def value_width(self):
        width = 0
        for item in self.items.values():
            width += item.width()
        return width

    def value_height(self):
        height = 0
        for item in self.items.values():
            height += item.height()
        return height

    def width(self):
        return self._width

    def height(self):
        return self._height

    def draw(self, path=None):
        dir_path = os.path.dirname(self.dst_path)
        if not os.path.exists(dir_path):
            os.makedirs(dir_path)

        bg_color = self.style["bg-color"]
        image = Image.new("RGB", (self.width(), self.height()), color=bg_color)
        drawer = ImageDraw.Draw(image)
        for item in self.items.values():
            item.draw(image, drawer)

        image.save(self.dst_path)
        self.reset()

    def collect_data(self):
        output = {}
        output["width"] = self.width()
        output["height"] = self.height()
        output["slate_path"] = self.dst_path

        placeholders = self.find_item(obj_type="placeholder")
        placeholders_data = []
        for placeholder in placeholders:
            placeholders_data.append(placeholder.collect_data())

        output["placeholders"] = placeholders_data

        return output
