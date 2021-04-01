import os
import sys
import collections

from PIL import ImageFont


class FontFactory:
    fonts = None
    default = None

    @classmethod
    def get_font(cls, family, font_size=None, italic=False, bold=False):
        if cls.fonts is None:
            cls.load_fonts()

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
            return cls.default

        font = family_styles.get(style)
        if font:
            if font_size:
                font = font.font_variant(size=font_size)
            return font

        # Return first found
        for font in family_styles:
            if font_size:
                font = font.font_variant(size=font_size)
            return font

        return cls.default

    @classmethod
    def load_fonts(cls):

        cls.default = ImageFont.load_default()

        available_font_ext = [".ttf", ".ttc"]
        dirs = []
        if sys.platform == "win32":
            # check the windows font repository
            # NOTE: must use uppercase WINDIR, to work around bugs in
            # 1.5.2's os.environ.get()
            windir = os.environ.get("WINDIR")
            if windir:
                dirs.append(os.path.join(windir, "fonts"))

        elif sys.platform in ("linux", "linux2"):
            lindirs = os.environ.get("XDG_DATA_DIRS", "")
            if not lindirs:
                # According to the freedesktop spec, XDG_DATA_DIRS should
                # default to /usr/share
                lindirs = "/usr/share"
            dirs += [
                os.path.join(lindir, "fonts") for lindir in lindirs.split(":")
            ]

        elif sys.platform == "darwin":
            dirs += [
                "/Library/Fonts",
                "/System/Library/Fonts",
                os.path.expanduser("~/Library/Fonts")
            ]

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

        cls.fonts = available_fonts
