import os
import json
import collections
from openpype import resources
from avalon.vendor import qtawesome


def load_stylesheet():
    from . import qrc_resources

    qrc_resources.qInitResources()

    current_dir = os.path.dirname(os.path.abspath(__file__))
    style_path = os.path.join(current_dir, "style.css")
    with open(style_path, "r") as style_file:
        stylesheet = style_file.read()

    data_path = os.path.join(current_dir, "data.json")
    with open(data_path, "r") as data_stream:
        data = json.load(data_stream)

    data_deque = collections.deque()
    for item in data.items():
        data_deque.append(item)

    fill_data = {}
    while data_deque:
        key, value = data_deque.popleft()
        if isinstance(value, dict):
            for sub_key, sub_value in value.items():
                new_key = "{}:{}".format(key, sub_key)
                data_deque.append((new_key, sub_value))
            continue
        fill_data[key] = value

    for key, value in fill_data.items():
        replacement_key = "{" + key + "}"
        stylesheet = stylesheet.replace(replacement_key, value)
    return stylesheet


def app_icon_path():
    return resources.pype_icon_filepath()
