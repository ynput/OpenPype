import re


def parse_color(value):
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
    from Qt import QtGui

    return QtGui.QColor(*args)


def min_max_check(value, min_value, max_value):
    if min_value is not None and value < min_value:
        raise ValueError("Minimum expected value is '{}' got '{}'".format(
            min_value, value
        ))

    if max_value is not None and value > max_value:
        raise ValueError("Maximum expected value is '{}' got '{}'".format(
            min_value, value
        ))


def int_validation(value, min_value=None, max_value=None):
    if not isinstance(value, int):
        raise TypeError((
            "Invalid type of hue expected 'int' got {}"
        ).format(str(type(value))))

    min_max_check(value, min_value, max_value)


def float_validation(value, min_value=None, max_value=None):
    if not isinstance(value, float):
        raise TypeError((
            "Invalid type of hue expected 'int' got {}"
        ).format(str(type(value))))

    min_max_check(value, min_value, max_value)


class UnknownColor:
    def __init__(self, value):
        self.value = value

    def get_qcolor(self):
        return create_qcolor(self.value)


class HEXColor:
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

        if isinstance(alpha, int):
            alpha = float(alpha)

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
