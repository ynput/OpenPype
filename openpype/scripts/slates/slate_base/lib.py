import os
import json
import logging
try:
    from queue import Queue
except Exception:
    from Queue import Queue

from .main_frame import MainFrame
from .layer import Layer
from .items import (
    ItemTable, ItemImage, ItemRectangle, ItemPlaceHolder, ItemText
)

log = logging.getLogger(__name__)


def slate_generator(
    fill_data, slate_settings, output_path,
    width=None, height=None, fonts_dir=None
):
    """Command line script for dynamic creatign of slates with PIL.

    Args:
        fill_data (dict): data used for formating inputs in slate_settings
        slate_settings (dict): slate settings template for slate layout
        output_path (str): path string including file extension
                           - this will define the output format.
        width (int, optional): expected width of slate image. Defaults to None.
        height (int, optional): expected height of slate image.
                                Defaults to None.
    """
    width = width or 1920
    height = height or 1080
    style = slate_settings.get("style") or {}

    main = MainFrame(width, height, output_path, fill_data, style=style)

    load_queue = Queue()
    for item in slate_settings["items"]:
        load_queue.put((item, main))

    while not load_queue.empty():
        item_data, parent = load_queue.get()

        item_type = item_data["type"].lower()
        item_style = item_data.get("style", {})
        item_name = item_data.get("name")

        pos_x = item_data.get("pos_x")
        pos_y = item_data.get("pos_y")
        if parent.obj_type != "main_frame":
            if pos_x or pos_y:
                # TODO logging
                log.warning((
                    "You have specified `pos_x` and `pos_y` but won't be used."
                    " Possible only if parent of an item is `main_frame`."
                ))
            pos_x = None
            pos_y = None

        kwargs = {
            "parent": parent,
            "style": item_style,
            "name": item_name,
            "pos_x": pos_x,
            "pos_y": pos_y,
            "root_width": width,
            "root_height": height,
            "fonts_dir": fonts_dir
        }

        if item_type == "layer":
            direction = item_data.get("direction", 0)
            item_obj = Layer(direction, **kwargs)

            for item in item_data.get("items", []):
                load_queue.put((item, item_obj))

        elif item_type == "table":
            use_alternate_color = item_data.get("use_alternate_color", False)
            values = item_data.get("values") or []
            ItemTable(values, use_alternate_color, **kwargs)

        elif item_type == "image":
            path = item_data["path"]
            ItemImage(path, **kwargs)

        elif item_type == "text":
            value = item_data.get("value", "")
            ItemText(value, **kwargs)

        elif item_type == "rectangle":
            item_obj = ItemRectangle(**kwargs)
            for item in item_data.get("items", []):
                load_queue.put((item, item_obj))

        elif item_type == "placeholder":
            path = item_data["path"]
            ItemPlaceHolder(path, **kwargs)

        else:
            # TODO logging
            log.warning(
                "Not implemented object type `{}` - skipping".format(item_type)
            )

    main.draw()
    log.debug("Slate creation finished")
