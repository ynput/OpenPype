"""Color definitions that can be used to parse strings for stylesheet.

Each definition must have available method `get_qcolor` which should return
`QtGui.QColor` representation of the color.

# TODO create abstract class to force this method implementation

Usage: Some colors may be not be used only in stylesheet but is required to
use them in code too. To not hardcode these color values into code it is better
to use same colors that are available fro stylesheets.

It is possible that some colors may not be used in stylesheet at all and thei
definition is used only in code.
"""

import re


def parse_color(value):
    """Parse string value of color to one of objected representation.

    Args:
        value(str): Color definition usable in stylesheet.
    """
    modified_value = value.strip().lower()
    if modified_value.startswith("hsla"):
        return HSLAColor(value)

    if modified_value.startswith("hsl"):
        return HSLColor(value)

    if modified_value.startswith("#"):
        return HEXColor(value)

    if modified_value.startswith("rgba"):
        return RGBAColor(value)

    if modified_value.startswith("rgb"):
        return RGBColor(value)
    return UnknownColor(value)


def create_qcolor(*args):
    """Create QtGui.QColor object.

    Args:
        *args (tuple): It is possible to pass initialization arguments for
            Qcolor.
    """
    from Qt import QtGui

    return QtGui.QColor(*args)


def min_max_check(value, min_value, max_value):
    """Validate number value if is in passed range.

    Args:
        value (int, float): Value which is validated.
        min_value (int, float): Minimum possible value. Validation is skipped
            if passed value is None.
        max_value (int, float): Maximum possible value. Validation is skipped
            if passed value is None.

    Raises:
        ValueError: When 'value' is out of specified range.
    """
    if min_value is not None and value < min_value:
        raise ValueError("Minimum expected value is '{}' got '{}'".format(
            min_value, value
        ))

    if max_value is not None and value > max_value:
        raise ValueError("Maximum expected value is '{}' got '{}'".format(
            min_value, value
        ))


def int_validation(value, min_value=None, max_value=None):
    """Validation of integer value within range.

    Args:
        value (int): Validated value.
        min_value (int): Minimum possible value.
        max_value (int): Maximum possible value.

    Raises:
        TypeError: If 'value' is not 'int' type.
    """
    if not isinstance(value, int):
        raise TypeError((
            "Invalid type of hue expected 'int' got {}"
        ).format(str(type(value))))

    min_max_check(value, min_value, max_value)


def float_validation(value, min_value=None, max_value=None):
    """Validation of float value within range.

    Args:
        value (float): Validated value.
        min_value (float): Minimum possible value.
        max_value (float): Maximum possible value.

    Raises:
        TypeError: If 'value' is not 'float' type.
    """
    if not isinstance(value, float):
        raise TypeError((
            "Invalid type of hue expected 'int' got {}"
        ).format(str(type(value))))

    min_max_check(value, min_value, max_value)


class UnknownColor:
    """Color from stylesheet data without known color definition.

    This is backup for unknown color definitions which may be for example
    constants or definition not yet defined by class.
    """
    def __init__(self, value):
        self.value = value

    def get_qcolor(self):
        return create_qcolor(self.value)


class HEXColor:
    """Hex color definition.

    Hex color is defined by '#' and 3 or 6 hex values (0-F).

    Examples:
        "#fff"
        "#f3f3f3"
    """
    regex = re.compile(r"[a-fA-F0-9]{3}(?:[a-fA-F0-9]{3})?$")

    def __init__(self, color_string):
        red, green, blue = self.hex_to_rgb(color_string)

        self._color_string = color_string
        self._red = red
        self._green = green
        self._blue = blue

    @property
    def red(self):
        return self._red

    @property
    def green(self):
        return self._green

    @property
    def blue(self):
        return self._blue

    def to_stylesheet_str(self):
        return self._color_string

    @classmethod
    def hex_to_rgb(cls, value):
        """Convert hex value to rgb."""
        hex_value = value.lstrip("#")
        if not cls.regex.match(hex_value):
            raise ValueError("\"{}\" is not a valid HEX code.".format(value))

        output = []
        if len(hex_value) == 3:
            for char in hex_value:
                output.append(int(char * 2, 16))
        else:
            for idx in range(3):
                start_idx = idx * 2
                output.append(int(hex_value[start_idx:start_idx + 2], 16))
        return output

    def get_qcolor(self):
        return create_qcolor(self.red, self.green, self.blue)


class RGBColor:
    """Color defined by red green and blue values.

    Each color has possible integer range 0-255.

    Examples:
        "rgb(255, 127, 0)"
    """
    def __init__(self, value):
        modified_color = value.lower().strip()
        content = modified_color.rstrip(")").lstrip("rgb(")
        red_str, green_str, blue_str = (
            item.strip() for item in content.split(",")
        )
        red = int(red_str)
        green = int(green_str)
        blue = int(blue_str)

        int_validation(red, 0, 255)
        int_validation(green, 0, 255)
        int_validation(blue, 0, 255)

        self._red = red
        self._green = green
        self._blue = blue

    @property
    def red(self):
        return self._red

    @property
    def green(self):
        return self._green

    @property
    def blue(self):
        return self._blue

    def get_qcolor(self):
        return create_qcolor(self.red, self.green, self.blue)


class RGBAColor:
    """Color defined by red green, blue and alpha values.

    Each color has possible integer range 0-255.

    Examples:
        "rgba(255, 127, 0, 127)"
    """
    def __init__(self, value):
        modified_color = value.lower().strip()
        content = modified_color.rstrip(")").lstrip("rgba(")
        red_str, green_str, blue_str, alpha_str = (
            item.strip() for item in content.split(",")
        )
        red = int(red_str)
        green = int(green_str)
        blue = int(blue_str)
        if "." in alpha_str:
            alpha = int(float(alpha_str) * 100)
        else:
            alpha = int(alpha_str)

        int_validation(red, 0, 255)
        int_validation(green, 0, 255)
        int_validation(blue, 0, 255)
        int_validation(alpha, 0, 255)

        self._red = red
        self._green = green
        self._blue = blue
        self._alpha = alpha

    @property
    def red(self):
        return self._red

    @property
    def green(self):
        return self._green

    @property
    def blue(self):
        return self._blue

    @property
    def alpha(self):
        return self._alpha

    def get_qcolor(self):
        return create_qcolor(self.red, self.green, self.blue, self.alpha)


class HSLColor:
    """Color defined by hue, saturation and light values.

    Hue is defined as integer in rage 0-360. Saturation and light can be
    defined as float or percent value.

    Examples:
        "hsl(27, 0.7, 0.3)"
        "hsl(27, 70%, 30%)"
    """
    def __init__(self, value):
        modified_color = value.lower().strip()
        content = modified_color.rstrip(")").lstrip("hsl(")
        hue_str, sat_str, light_str = (
            item.strip() for item in content.split(",")
        )
        hue = int(hue_str) % 360
        if "%" in sat_str:
            sat = float(sat_str.rstrip("%")) / 100
        else:
            sat = float(sat)

        if "%" in light_str:
            light = float(light_str.rstrip("%")) / 100
        else:
            light = float(light_str)

        int_validation(hue, 0, 360)
        float_validation(sat, 0, 1)
        float_validation(light, 0, 1)

        self._hue = hue
        self._saturation = sat
        self._light = light

    @property
    def hue(self):
        return self._hue

    @property
    def saturation(self):
        return self._saturation

    @property
    def light(self):
        return self._light

    def get_qcolor(self):
        color = create_qcolor()
        color.setHslF(self.hue / 360, self.saturation, self.light)
        return color


class HSLAColor:
    """Color defined by hue, saturation, light and alpha values.

    Hue is defined as integer in rage 0-360. Saturation and light can be
    defined as float (0-1 range) or percent value(0-100%). And alpha
    as float (0-1 range).

    Examples:
        "hsl(27, 0.7, 0.3)"
        "hsl(27, 70%, 30%)"
    """
    def __init__(self, value):
        modified_color = value.lower().strip()
        content = modified_color.rstrip(")").lstrip("hsla(")
        hue_str, sat_str, light_str, alpha_str = (
            item.strip() for item in content.split(",")
        )
        hue = int(hue_str) % 360
        if "%" in sat_str:
            sat = float(sat_str.rstrip("%")) / 100
        else:
            sat = float(sat)

        if "%" in light_str:
            light = float(light_str.rstrip("%")) / 100
        else:
            light = float(light_str)

        alpha = float(alpha_str)

        int_validation(hue, 0, 360)
        float_validation(sat, 0, 1)
        float_validation(light, 0, 1)
        float_validation(alpha, 0, 1)

        self._hue = hue
        self._saturation = sat
        self._light = light
        self._alpha = alpha

    @property
    def hue(self):
        return self._hue

    @property
    def saturation(self):
        return self._saturation

    @property
    def light(self):
        return self._light

    @property
    def alpha(self):
        return self._alpha

    def get_qcolor(self):
        color = create_qcolor()
        color.setHslF(self.hue / 360, self.saturation, self.light, self.alpha)
        return color
