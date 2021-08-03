import os
import sys
import collections

from PIL import ImageFont


class FontFactory:
    fonts = None
    default = None
    default_font_name = "courier new"

    @classmethod
    def get_font(cls, klass, family, font_size=None, italic=False,
                 bold=False, fonts_dir=None):
        if cls.fonts is None:
            cls.load_fonts(fonts_dir)

        styles = []
        if bold:
            styles.append("Bold")

        if italic:
            styles.append("Italic")

        if not styles:
            styles.append("Regular")

        style = " ".join(styles)
        family = family.lower()
        family_styles = cls.fonts.get(family)
        if not family_styles:
            for _font in cls.default:
                klass.log.warning((
                    "Missing font '{}', "
                    "is replaced with default '{}'").format(
                        family, cls.default_font_name))
                font = cls.default[_font].font_variant(size=font_size)
            return font

        font = family_styles.get(style)
        if font:
            if font_size:
                font = font.font_variant(size=font_size)
            return font

        # If missing variant return first found
        for _font in family_styles:
            if font_size:
                klass.log.warning((
                    "Missing font '{}' with variant '{}', "
                    "is replaced with '{}' variant").format(
                        family, style, _font))
                font = family_styles[_font].font_variant(size=font_size)
            return font

        return cls.default

    @classmethod
    def load_fonts(cls, fonts_dir=None):

        available_font_ext = [".ttf", ".ttc"]
        dirs = []
        if sys.platform == "win32":
            # check the windows font repository
            # NOTE: must use uppercase WINDIR, to work around bugs in
            # 1.5.2's os.environ.get()
            windir = os.environ.get("WINDIR")
            if windir:
                dirs.append(os.path.join(windir, "fonts"))
            if fonts_dir:
                dirs.append(os.path.normpath(fonts_dir))

        elif sys.platform in ("linux", "linux2"):
            lindirs = os.environ.get("XDG_DATA_DIRS", "")
            if not lindirs:
                # According to the freedesktop spec, XDG_DATA_DIRS should
                # default to /usr/share
                lindirs = "/usr/share"
            dirs += [
                os.path.join(lindir, "fonts") for lindir in lindirs.split(":")
            ]
            if fonts_dir:
                dirs.append(os.path.normpath(fonts_dir))

        elif sys.platform == "darwin":
            dirs += [
                "/Library/Fonts",
                "/System/Library/Fonts",
                os.path.expanduser("~/Library/Fonts")
            ]
            if fonts_dir:
                dirs.append(os.path.normpath(fonts_dir))

        available_fonts = collections.defaultdict(dict)
        for directory in dirs:
            for walkroot, walkdir, walkfilenames in os.walk(directory):
                for walkfilename in walkfilenames:
                    ext = os.path.splitext(walkfilename)[1]
                    if ext.lower() not in available_font_ext:
                        continue

                    fontpath = os.path.join(walkroot, walkfilename)
                    font_obj = ImageFont.truetype(fontpath)
                    family = font_obj.font.family.lower()
                    style = font_obj.font.style
                    available_fonts[family][style] = font_obj

        cls.default = available_fonts.get(cls.default_font_name)
        cls.fonts = available_fonts
