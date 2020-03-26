import logging

try:
    from queue import Queue
except Exception:
    from Queue import Queue

from .slate_base.main_frame import MainFrame
from .slate_base.layer import Layer
from .slate_base.items import (
    ItemTable, ItemImage, ItemRectangle, ItemPlaceHolder
)

from pypeapp import config

log = logging.getLogger(__name__)


RequiredSlateKeys = ["width", "height", "destination_path"]


def create_slates(fill_data, slate_name):
    presets = config.get_presets()
    slate_presets = (
        presets
        .get("tools", {})
        .get("slates")
    ) or {}
    slate_data = slate_presets.get(slate_name)

    if not slate_data:
        log.error("Slate data of <{}> does not exists.")
        return False

    missing_keys = []
    for key in RequiredSlateKeys:
        if key not in slate_data:
            missing_keys.append("`{}`".format(key))

    if missing_keys:
        log.error("Slate data of <{}> miss required keys: {}".format(
            slate_name, ", ".join(missing_keys)
        ))
        return False

    width = slate_data["width"]
    height = slate_data["height"]
    dst_path = slate_data["destination_path"]
    style = slate_data.get("style") or {}

    main = MainFrame(width, height, dst_path, fill_data, style=style)

    load_queue = Queue()
    for item in slate_data["items"]:
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
            "pos_y": pos_y
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

        elif item_type == "rectangle":
            ItemRectangle(**kwargs)

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


def example():
    # import sys
    # sys.append(r"PATH/TO/PILLOW/PACKAGE")
    # sys.append(r"PATH/TO/PYPE-SETUP")

    fill_data = {
        "destination_path": "PATH/TO/OUTPUT/FILE",
        "project": {
            "name": "Testing project"
        },
        "intent": "WIP",
        "version_name": "seq01_sh0100_compositing_v01",
        "date": "2019-08-09",
        "shot_type": "2d comp",
        "submission_note": (
            "Lorem ipsum dolor sit amet, consectetuer adipiscing elit."
            " Aenean commodo ligula eget dolor. Aenean massa."
            " Cum sociis natoque penatibus et magnis dis parturient montes,"
            " nascetur ridiculus mus. Donec quam felis, ultricies nec,"
            " pellentesque eu, pretium quis, sem. Nulla consequat massa quis"
            " enim. Donec pede justo, fringilla vel,"
            " aliquet nec, vulputate eget, arcu."
        ),
        "thumbnail_path": "PATH/TO/THUMBNAIL/FILE",
        "color_bar_path": "PATH/TO/COLOR/BAR/FILE",
        "vendor": "Our Studio",
        "shot_name": "sh0100",
        "frame_start": 1001,
        "frame_end": 1004,
        "duration": 3
    }
    create_slates(fill_data, "example_HD")


if __name__ == "__main__":
    example()
