import os
import json
import collections
import six

from openpype import resources

from .color_defs import parse_color

current_dir = os.path.dirname(os.path.abspath(__file__))


# Default colors
# - default color used in tool icons
_TOOLS_ICON_COLOR = "#ffffff"
# - entities icon color - use 'get_default_asset_icon_color'
_DEFAULT_ENTITY_ICON_COLOR = "#fb9c15"
# - disabled entitie
_DISABLED_ENTITY_ICON_ICON_COLOR = "#808080"
# - deprecated entity font color
_DEPRECATED_ENTITY_FONT_COLOR = "#666666"


class _Cache:
    stylesheet = None
    font_ids = None

    tools_icon_color = None
    default_entity_icon_color = None
    disabled_entity_icon_color = None
    deprecated_entity_font_color = None


def get_style_image_path(image_name):
    # All filenames are lowered
    image_name = image_name.lower()
    # Male sure filename has png extension
    if not image_name.endswith(".png"):
        image_name += ".png"
    filepath = os.path.join(current_dir, "images", image_name)
    if os.path.exists(filepath):
        return filepath
    return None


def _get_colors_raw_data():
    """Read data file with stylesheet fill values.

    Returns:
        dict: Loaded data for stylesheet.
    """
    data_path = os.path.join(current_dir, "data.json")
    with open(data_path, "r") as data_stream:
        data = json.load(data_stream)
    return data


def get_colors_data():
    """Only color data from stylesheet data."""
    data = _get_colors_raw_data()
    return data.get("color") or {}


def _convert_color_values_to_objects(value):
    """Parse all string values in dictionary to Color definitions.

    Recursive function calling itself if value is dictionary.

    Args:
        value (dict, str): String is parsed into color definition object and
            dictionary is passed into this function.

    Raises:
        TypeError: If value in color data do not contain string of dictionary.
    """
    if isinstance(value, dict):
        output = {}
        for _key, _value in value.items():
            output[_key] = _convert_color_values_to_objects(_value)
        return output

    if not isinstance(value, six.string_types):
        raise TypeError((
            "Unexpected type in colors data '{}'. Expected 'str' or 'dict'."
        ).format(str(type(value))))
    return parse_color(value)


def get_objected_colors():
    """Colors parsed from stylesheet data into color definitions.

    Returns:
        dict: Parsed color objects by keys in data.
    """
    colors_data = get_colors_data()
    output = {}
    for key, value in colors_data.items():
        output[key] = _convert_color_values_to_objects(value)
    return output


def _load_stylesheet():
    """Load strylesheet and trigger all related callbacks.

    Style require more than a stylesheet string. Stylesheet string
    contains paths to resources which must be registered into Qt application
    and load fonts used in stylesheets.

    Also replace values from stylesheet data into stylesheet text.
    """
    from . import qrc_resources

    qrc_resources.qInitResources()

    style_path = os.path.join(current_dir, "style.css")
    with open(style_path, "r") as style_file:
        stylesheet = style_file.read()

    data = _get_colors_raw_data()

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
    """Load and register fonts into Qt application."""
    from Qt import QtGui

    # Check if font ids are still loaded
    if _Cache.font_ids is not None:
        for font_id in tuple(_Cache.font_ids):
            font_families = QtGui.QFontDatabase.applicationFontFamilies(
                font_id
            )
            # Reset font if font id is not available
            if not font_families:
                _Cache.font_ids = None
                break

    if _Cache.font_ids is None:
        _Cache.font_ids = []
        fonts_dirpath = os.path.join(current_dir, "fonts")
        font_dirs = []
        font_dirs.append(os.path.join(fonts_dirpath, "Noto_Sans"))
        font_dirs.append(os.path.join(
            fonts_dirpath,
            "Noto_Sans_Mono",
            "static",
            "NotoSansMono"
        ))

        loaded_fonts = []
        for font_dir in font_dirs:
            for filename in os.listdir(font_dir):
                if os.path.splitext(filename)[1] not in [".ttf"]:
                    continue
                full_path = os.path.join(font_dir, filename)
                font_id = QtGui.QFontDatabase.addApplicationFont(full_path)
                _Cache.font_ids.append(font_id)
                font_families = QtGui.QFontDatabase.applicationFontFamilies(
                    font_id
                )
                loaded_fonts.extend(font_families)
        print("Registered font families: {}".format(", ".join(loaded_fonts)))


def load_stylesheet():
    """Load and return OpenPype Qt stylesheet."""

    if _Cache.stylesheet is None:
        _Cache.stylesheet = _load_stylesheet()
    _load_font()
    return _Cache.stylesheet


def get_app_icon_path():
    """Path to OpenPype icon."""
    return resources.get_openpype_icon_filepath()


def app_icon_path():
    # Backwards compatibility
    return get_app_icon_path()


def get_default_tools_icon_color():
    if _Cache.tools_icon_color is None:
        color_data = get_colors_data()
        color = color_data.get("icon-tools")
        _Cache.tools_icon_color = color or _TOOLS_ICON_COLOR
    return _Cache.tools_icon_color


def get_default_entity_icon_color():
    if _Cache.default_entity_icon_color is None:
        color_data = get_colors_data()
        color = color_data.get("icon-entity-default")
        _Cache.default_entity_icon_color = color or _DEFAULT_ENTITY_ICON_COLOR
    return _Cache.default_entity_icon_color


def get_disabled_entity_icon_color():
    if _Cache.disabled_entity_icon_color is None:
        color_data = get_colors_data()
        color = color_data.get("icon-entity-disabled")
        _Cache.disabled_entity_icon_color = (
            color or _DISABLED_ENTITY_ICON_ICON_COLOR
        )
    return _Cache.disabled_entity_icon_color


def get_deprecated_entity_font_color():
    if _Cache.deprecated_entity_font_color is None:
        color_data = get_colors_data()
        color = color_data.get("font-entity-deprecated")
        _Cache.deprecated_entity_font_color = (
            color or _DEPRECATED_ENTITY_FONT_COLOR
        )
    return _Cache.deprecated_entity_font_color
