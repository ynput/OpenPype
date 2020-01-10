import textwrap
from PIL import Image, ImageFont, ImageDraw, ImageEnhance, ImageColor


class TableDraw:
    def __init__(
        self, image_width, image_height,
        rel_pos_x, rel_pos_y, rel_width,
        col_fonts=None, col_font_colors=None,
        default_font=None, default_font_color=None,
        col_alignments=None, rel_col_widths=None, bg_color=None,
        alter_bg_color=None, pad=20,
        pad_top=None, pad_bottom=None, pad_left=None, pad_right=None
    ):
        self.image_width = image_width

        pos_x = image_width * rel_pos_x
        pos_y = image_height * rel_pos_y
        width = image_width * rel_width

        self.pos_x_start = pos_x
        self.pos_y_start = pos_y
        self.pos_x_end = pos_x + width
        self.width = width

        self.rel_col_widths = list(rel_col_widths)
        self._col_widths = None
        self._col_alignments = col_alignments

        if bg_color and isinstance(bg_color, str):
            bg_color = ImageColor.getrgb(bg_color)

        if alter_bg_color and isinstance(alter_bg_color, str):
            alter_bg_color = ImageColor.getrgb(alter_bg_color)

        self._bg_color = bg_color
        self._alter_bg_color = alter_bg_color

        self.alter_use = False

        if col_fonts:
            _col_fonts = []
            for col_font in col_fonts:
                font_name, font_size = col_font
                font = ImageFont.truetype(font_name, font_size)
                _col_fonts.append(font)
            col_fonts = _col_fonts

        self._col_fonts = col_fonts

        self._col_font_colors = col_font_colors

        if not default_font:
            default_font = ImageFont.truetype("times", 26)
        self.default_font = default_font

        if not default_font_color:
            default_font_color = "#ffffff"
        self.default_font_color = default_font_color

        self.texts = []

        if pad is None:
            pad = 5

        _pad_top = pad
        if pad_top is not None:
            _pad_top = pad_top

        _pad_bottom = pad
        if pad_bottom is not None:
            _pad_bottom = pad_bottom

        _pad_left = pad
        if pad_left is not None:
            _pad_left = pad_left

        _pad_right = pad
        if pad_right is not None:
            _pad_right = pad_right

        self.pad_top = _pad_top
        self.pad_bottom = _pad_bottom
        self.pad_left = _pad_left
        self.pad_right = _pad_right

    @property
    def col_widths(self):
        if self._col_widths is None:
            sum_width = 0
            for w in self.rel_col_widths:
                sum_width += w

            one_piece = self.width / sum_width
            self._col_widths = []
            for w in self.rel_col_widths:
                self._col_widths.append(one_piece * w)

        return self._col_widths

    @property
    def col_fonts(self):
        if self._col_fonts is None:
            self._col_fonts = []
            for _ in range(len(self.col_widths)):
                self._col_fonts.append(self.default_font)

        elif len(self._col_fonts) < len(self.col_widths):
            if isinstance(self._col_fonts, tuple):
                self._col_fonts = list(self._col_fonts)

            while len(self._col_fonts) < len(self.col_widths):
                self._col_fonts.append(self.default_font)

        return self._col_fonts

    @property
    def col_font_colors(self):
        if self._col_font_colors is None:
            self._col_font_colors = []
            for _ in range(len(self.col_widths)):
                self._col_font_colors.append(self.default_font_color)

        elif len(self._col_font_colors) < len(self.col_widths):
            if isinstance(self._col_font_colors, tuple):
                self._col_font_colors = list(self._col_font_colors)

            while len(self._col_font_colors) < len(self.col_widths):
                self._col_font_colors.append(self.default_font_color)

        return self._col_font_colors

    @property
    def col_alignments(self):
        if self._col_alignments is None:
            self._col_alignments = []
            for _ in range(len(self.col_widths)):
                self._col_alignments.append("left")

        elif len(self._col_alignments) < len(self.col_widths):
            if isinstance(self._col_alignments, tuple):
                self._col_alignments = list(self._col_alignments)

            while len(self._col_alignments) < len(self.col_widths):
                self._col_alignments.append("left")

        return self._col_alignments

    @property
    def bg_color(self):
        if self.alter_use is True:
            value = self.alter_bg_color
            self.alter_use = False
        else:
            value = self._bg_color
            self.alter_use = True
        return value

    @property
    def alter_bg_color(self):
        if self._alter_bg_color:
            return self._alter_bg_color
        return self.bg_color

    def add_texts(self, texts):
        if isinstance(texts, str):
            texts = [texts]

        for text in texts:
            if isinstance(text, str):
                text = [text]

            if len(text) > len(self.rel_col_widths):
                for _ in (len(text) - len(self.rel_col_widths)):
                    self.rel_col_widths.append(1)
                    for _t in self.texts:
                        _t.append("")

            self.texts.append(text)

    def draw(self, drawer):
        y_pos = self.pos_y_start
        for texts in self.texts:
            max_height = None
            cols_data = []
            for _idx, col in enumerate(texts):
                width = self.col_widths[_idx]
                font = self.col_fonts[_idx]
                lines, line_height = self.lines_height_by_width(
                    drawer, col, width - self.pad_left - self.pad_right, font
                )
                row_height = line_height * len(lines)
                if max_height is None or row_height > max_height:
                    max_height = row_height

                cols_data.append({
                    "lines": lines,
                    "line_height": line_height
                })

            drawer.rectangle(
                (
                    (self.pos_x_start, y_pos),
                    (
                        self.pos_x_end,
                        y_pos + max_height + self.pad_top + self.pad_bottom
                    )
                ),
                fill=self.bg_color
            )

            pos_x_start = self.pos_x_start + self.pad_left
            for col, col_data in enumerate(cols_data):
                lines = col_data["lines"]
                line_height = col_data["line_height"]
                alignment = self.col_alignments[col]
                x_offset = self.col_widths[col]
                font = self.col_fonts[col]
                font_color = self.col_font_colors[col]
                for idx, line_data in enumerate(lines):
                    line = line_data["text"]
                    line_width = line_data["width"]
                    if alignment == "left":
                        x_start = pos_x_start + self.pad_left
                    elif alignment == "right":
                        x_start = (
                            pos_x_start + x_offset - line_width -
                            self.pad_right - self.pad_left
                        )
                    else:
                        # TODO else
                        x_start = pos_x_start + self.pad_left

                    drawer.text(
                        (
                            x_start,
                            y_pos + (idx * line_height) + self.pad_top
                        ),
                        line,
                        font=font,
                        fill=font_color
                    )
                pos_x_start += x_offset

            y_pos += max_height + self.pad_top + self.pad_bottom

    def lines_height_by_width(self, drawer, text, width, font):
        lines = []
        lines.append([part for part in text.split() if part])

        line = 0
        while True:
            thistext = lines[line]
            line = line + 1
            if not thistext:
                break
            newline = []

            while True:
                _textwidth = drawer.textsize(" ".join(thistext), font)[0]
                if (
                    _textwidth <= width
                ):
                    break
                elif _textwidth > width and len(thistext) == 1:
                    # TODO raise error?
                    break

                val = thistext.pop(-1)

                if not val:
                    break
                newline.insert(0, val)

            if len(newline) > 0:
                lines.append(newline)
            else:
                break

        _lines = []
        height = None
        for line_items in lines:
            line = " ".join(line_items)
            (width, _height) = drawer.textsize(line, font)
            if height is None or height < _height:
                height = _height

            _lines.append({
                "width": width,
                "text": line
            })

        return (_lines, height)


width = 1920
height = 1080
# width = 800
# height = 600
bg_color_hex = "#242424"
bg_color = ImageColor.getrgb(bg_color_hex)

base = Image.new('RGB', (width, height), color=bg_color)

texts = [
    ("Version name:", "mei_101_001_0020_slate_NFX_v001"),
    ("Date:", "2019-08-09"),
    ("Shot Types:", "2d comp"),
    # ("Submission Note:", "Submitting as and example with all MEI fields filled out. As well as the additional fields Shot description, Episode, Scene, and Version # that were requested by production.")
]
text_widths_rel = (2, 8)
col_alignments = ("right", "left")
fonts = (("arial", 20), ("times", 26))
font_colors = ("#999999", "#ffffff")

table_color_hex = "#212121"
table_alter_color_hex = "#272727"

drawer = ImageDraw.Draw(base)
table_d = TableDraw(
    width, height,
    0.1, 0.1, 0.5,
    col_fonts=fonts,
    col_font_colors=font_colors,
    rel_col_widths=text_widths_rel,
    col_alignments=col_alignments,
    bg_color=table_color_hex,
    alter_bg_color=table_alter_color_hex,
    pad_top=20, pad_bottom=20, pad_left=5, pad_right=5
)

table_d.add_texts(texts)
table_d.draw(drawer)

image_path = r"C:\Users\iLLiCiT\Desktop\Prace\Pillow\image.jpg"
image = Image.open(image_path)
img_width, img_height = image.size

rel_image_width = 0.3
rel_image_pos_x = 0.65
rel_image_pos_y = 0.1
image_pos_x = int(width * rel_image_pos_x)
image_pos_y = int(width * rel_image_pos_y)

new_width = int(width * rel_image_width)
new_height = int(new_width * img_height / img_width)
image = image.resize((new_width, new_height), Image.ANTIALIAS)

# mask = Image.new("L", image.size, 255)

base.paste(image, (image_pos_x, image_pos_y))
base.save(r"C:\Users\iLLiCiT\Desktop\Prace\Pillow\test{}x{}.jpg".format(
    width, height
))
base.show()
