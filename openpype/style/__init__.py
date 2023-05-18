import os
import copy
import json
import collections
import six

from openpype import resources

from .color_defs import parse_color

current_dir = os.path.dirname(os.path.abspath(__file__))


class _Cache:
    stylesheet = None
    font_ids = None

    tools_icon_color = None
    default_entity_icon_color = None
    disabled_entity_icon_color = None
    deprecated_entity_font_color = None

    colors_data = None
    objected_colors = None


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
    if _Cache.colors_data is None:
        data = _get_colors_raw_data()
        color_data = data.get("color") or {}
        _Cache.colors_data = color_data
    return copy.deepcopy(_Cache.colors_data)


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


def get_objected_colors(*keys):
    """Colors parsed from stylesheet data into color definitions.

    You can pass multiple arguments to get a key from the data dict's colors.
    Because this functions returns a deep copy of the cached data this allows
    a much smaller dataset to be copied and thus result in a faster function.
    It is however a micro-optimization in the area of 0.001s and smaller.

    For example:
        >>> get_colors_data()           # copy of full colors dict
        >>> get_colors_data("font")
        >>> get_colors_data("loader", "asset-view")

    Args:
        *keys: Each key argument will return a key nested deeper in the
            objected colors data.

    Returns:
        Any: Parsed color objects by keys in data.
    """
    if _Cache.objected_colors is None:
        colors_data = get_colors_data()
        output = {}
        for key, value in colors_data.items():
            output[key] = _convert_color_values_to_objects(value)

        _Cache.objected_colors = output

    output = _Cache.objected_colors
    for key in keys:
        output = output[key]
    return copy.deepcopy(output)


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
    from qtpy import QtGui

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
    """Default color used in tool icons.

    Color must be possible to parse using QColor.

    Returns:
        str: Color as a string.
    """
    if _Cache.tools_icon_color is None:
        color_data = get_colors_data()
        _Cache.tools_icon_color = color_data["icon-tools"]
    return _Cache.tools_icon_color


def get_default_entity_icon_color():
    """Default color of entities icons.

    Color must be possible to parse using QColor.

    Returns:
        str: Color as a string.
    """
    if _Cache.default_entity_icon_color is None:
        color_data = get_colors_data()
        _Cache.default_entity_icon_color = color_data["icon-entity-default"]
    return _Cache.default_entity_icon_color


def get_disabled_entity_icon_color():
    """Default color of entities icons.

    TODO: Find more suitable function name.

    Color must be possible to parse using QColor.

    Returns:
        str: Color as a string.
    """
    if _Cache.disabled_entity_icon_color is None:
        color_data = get_colors_data()
        _Cache.disabled_entity_icon_color = color_data["icon-entity-disabled"]
    return _Cache.disabled_entity_icon_color


def get_deprecated_entity_font_color():
    """Font color for deprecated entities.

    Color must be possible to parse using QColor.

    Returns:
        str: Color as a string.
    """
    if _Cache.deprecated_entity_font_color is None:
        color_data = get_colors_data()
        _Cache.deprecated_entity_font_color = (
            color_data["font-entity-deprecated"]
        )
    return _Cache.deprecated_entity_font_color
