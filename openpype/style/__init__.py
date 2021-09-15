import os
import json
import collections
from openpype import resources


_STYLESHEET_CACHE = None
_FONT_IDS = None

current_dir = os.path.dirname(os.path.abspath(__file__))


def _load_stylesheet():
    from . import qrc_resources

    qrc_resources.qInitResources()

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


def _load_font():
    from Qt import QtGui

    global _FONT_IDS

    # Check if font ids are still loaded
    if _FONT_IDS is not None:
        for font_id in tuple(_FONT_IDS):
            font_families = QtGui.QFontDatabase.applicationFontFamilies(
                font_id
            )
            # Reset font if font id is not available
            if not font_families:
                _FONT_IDS = None
                break

    if _FONT_IDS is None:
        _FONT_IDS = []
        fonts_dirpath = os.path.join(current_dir, "fonts")
        font_dirs = []
        font_dirs.append(os.path.join(fonts_dirpath, "Montserrat"))
        font_dirs.append(os.path.join(fonts_dirpath, "Spartan"))
        font_dirs.append(os.path.join(fonts_dirpath, "RobotoMono", "static"))

        loaded_fonts = []
        for font_dir in font_dirs:
            for filename in os.listdir(font_dir):
                if os.path.splitext(filename)[1] not in [".ttf"]:
                    continue
                full_path = os.path.join(font_dir, filename)
                font_id = QtGui.QFontDatabase.addApplicationFont(full_path)
                _FONT_IDS.append(font_id)
                font_families = QtGui.QFontDatabase.applicationFontFamilies(
                    font_id
                )
                loaded_fonts.extend(font_families)
        print("Registered font families: {}".format(", ".join(loaded_fonts)))


def load_stylesheet():
    global _STYLESHEET_CACHE
    if _STYLESHEET_CACHE is None:
        _STYLESHEET_CACHE = _load_stylesheet()
    _load_font()
    return _STYLESHEET_CACHE


def app_icon_path():
    return resources.pype_icon_filepath()
