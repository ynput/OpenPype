import os
import json
from queue import Queue

# --- Lines for debug purpose ---------------------------------
import sys
sys.path.append(r"C:\Users\Public\pype_env2\Lib\site-packages")
# -------------------------------------------------------------

from slate_base.main_frame import MainFrame
from slate_base.layer import Layer
from slate_base.items import (
    ItemTable, ItemImage, ItemRectangle, ItemPlaceHolder
)


def main(fill_data):
    cur_folder = os.path.dirname(os.path.abspath(__file__))
    input_json = os.path.join(cur_folder, "netflix_v03.json")
    with open(input_json) as json_file:
        slate_data = json.load(json_file)


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
                self.log.warning((
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
            self.log.warning(
                "Slate item not implemented <{}> - skipping".format(item_type)
            )

    main.draw()
    print("Slate creation finished")


if __name__ == "__main__":
    fill_data = {
        "destination_path": "C:/Users/jakub.trllo/Desktop/Tests/files/image/netflix_output_v03.png",
        "project": {
            "name": "Project name"
        },
        "intent": "WIP",
        "version_name": "mei_101_001_0020_slate_NFX_v001",
        "date": "2019-08-09",
        "shot_type": "2d comp",
        "submission_note": "Submitting as and example with all MEI fields filled out. As well as the additional fields Shot description, Episode, Scene, and Version # that were requested by production.",
        "thumbnail_path": "C:/Users/jakub.trllo/Desktop/Tests/files/image/birds.png",
        "color_bar_path": "C:/Users/jakub.trllo/Desktop/Tests/files/image/kitten.jpg",
        "vendor": "DAZZLE",
        "shot_name": "SLATE_SIMPLE",
        "frame_start": 1001,
        "frame_end": 1004,
        "duration": 3
    }
    main(fill_data)
    # raise NotImplementedError("Slates don't have Implemented args running")
