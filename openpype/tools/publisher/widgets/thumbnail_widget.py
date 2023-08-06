import os
import uuid

from qtpy import QtWidgets, QtCore, QtGui

from openpype.style import get_objected_colors
from openpype.lib import (
    run_subprocess,
    is_oiio_supported,
    get_oiio_tool_args,
    get_ffmpeg_tool_args,
)
from openpype.lib.transcoding import (
    IMAGE_EXTENSIONS,
    VIDEO_EXTENSIONS,
)

from openpype.tools.utils import (
    paint_image_with_color,
    PixmapButton,
)
from openpype.tools.publisher.control import CardMessageTypes

from .icons import get_image
from .screenshot_widget import capture_to_file


class ThumbnailPainterWidget(QtWidgets.QWidget):
    width_ratio = 3.0
    height_ratio = 2.0
    border_width = 1
    max_thumbnails = 3
    offset_sep = 4
    checker_boxes_count = 20

    def __init__(self, parent):
        super(ThumbnailPainterWidget, self).__init__(parent)

        border_color = get_objected_colors("bg-buttons").get_qcolor()
        thumbnail_bg_color = get_objected_colors("bg-view").get_qcolor()
        overlay_color = get_objected_colors("font").get_qcolor()

        default_image = get_image("thumbnail")
        default_pix = paint_image_with_color(default_image, border_color)

        self.border_color = border_color
        self.thumbnail_bg_color = thumbnail_bg_color
        self.overlay_color = overlay_color
        self._default_pix = default_pix

        self._cached_pix = None
        self._current_pixes = None
        self._has_pixes = False

    @property
    def has_pixes(self):
        return self._has_pixes

    def clear_cache(self):
        self._cached_pix = None
        self.repaint()

    def set_current_thumbnails(self, thumbnail_paths=None):
        pixes = []
        if thumbnail_paths:
            for thumbnail_path in thumbnail_paths:
                pixes.append(QtGui.QPixmap(thumbnail_path))

        self._current_pixes = pixes or None
        self._has_pixes = self._current_pixes is not None
        self.clear_cache()

    def paintEvent(self, event):
        if self._cached_pix is None:
            self._cache_pix()

        painter = QtGui.QPainter()
        painter.begin(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        painter.drawPixmap(0, 0, self._cached_pix)
        painter.end()

    def _paint_checker(self, width, height):
        checker_size = int(float(width) / self.checker_boxes_count)
        if checker_size < 1:
            checker_size = 1

        checker_pix = QtGui.QPixmap(checker_size * 2, checker_size * 2)
        checker_pix.fill(QtCore.Qt.transparent)
        checker_painter = QtGui.QPainter()
        checker_painter.begin(checker_pix)
        checker_painter.setPen(QtCore.Qt.NoPen)
        checker_painter.setBrush(QtGui.QColor(89, 89, 89))
        checker_painter.drawRect(
            0, 0, checker_pix.width(), checker_pix.height()
        )
        checker_painter.setBrush(QtGui.QColor(188, 187, 187))
        checker_painter.drawRect(
            0, 0, checker_size, checker_size
        )
        checker_painter.drawRect(
            checker_size, checker_size, checker_size, checker_size
        )
        checker_painter.end()
        return checker_pix

    def _paint_default_pix(self, pix_width, pix_height):
        full_border_width = 2 * self.border_width
        width = pix_width - full_border_width
        height = pix_height - full_border_width
        if width > 100:
            width = int(width * 0.6)
            height = int(height * 0.6)

        scaled_pix = self._default_pix.scaled(
            width,
            height,
            QtCore.Qt.KeepAspectRatio,
            QtCore.Qt.SmoothTransformation
        )
        pos_x = int(
            (pix_width - scaled_pix.width()) / 2
        )
        pos_y = int(
            (pix_height - scaled_pix.height()) / 2
        )
        new_pix = QtGui.QPixmap(pix_width, pix_height)
        new_pix.fill(QtCore.Qt.transparent)
        pix_painter = QtGui.QPainter()
        pix_painter.begin(new_pix)
        render_hints = (
            QtGui.QPainter.Antialiasing
            | QtGui.QPainter.SmoothPixmapTransform
        )
        if hasattr(QtGui.QPainter, "HighQualityAntialiasing"):
            render_hints |= QtGui.QPainter.HighQualityAntialiasing

        pix_painter.setRenderHints(render_hints)
        pix_painter.drawPixmap(pos_x, pos_y, scaled_pix)
        pix_painter.end()
        return new_pix

    def _draw_thumbnails(self, thumbnails, pix_width, pix_height):
        full_border_width = 2 * self.border_width

        checker_pix = self._paint_checker(pix_width, pix_height)

        backgrounded_images = []
        for src_pix in thumbnails:
            scaled_pix = src_pix.scaled(
                pix_width - full_border_width,
                pix_height - full_border_width,
                QtCore.Qt.KeepAspectRatio,
                QtCore.Qt.SmoothTransformation
            )
            pos_x = int(
                (pix_width - scaled_pix.width()) / 2
            )
            pos_y = int(
                (pix_height - scaled_pix.height()) / 2
            )

            new_pix = QtGui.QPixmap(pix_width, pix_height)
            new_pix.fill(QtCore.Qt.transparent)
            pix_painter = QtGui.QPainter()
            pix_painter.begin(new_pix)
            render_hints = (
                QtGui.QPainter.Antialiasing
                | QtGui.QPainter.SmoothPixmapTransform
            )
            if hasattr(QtGui.QPainter, "HighQualityAntialiasing"):
                render_hints |= QtGui.QPainter.HighQualityAntialiasing
            pix_painter.setRenderHints(render_hints)

            tiled_rect = QtCore.QRectF(
                pos_x, pos_y, scaled_pix.width(), scaled_pix.height()
            )
            pix_painter.drawTiledPixmap(
                tiled_rect,
                checker_pix,
                QtCore.QPointF(0.0, 0.0)
            )
            pix_painter.drawPixmap(pos_x, pos_y, scaled_pix)
            pix_painter.end()
            backgrounded_images.append(new_pix)
        return backgrounded_images

    def _paint_dash_line(self, painter, rect):
        pen = QtGui.QPen()
        pen.setWidth(1)
        pen.setBrush(QtCore.Qt.darkGray)
        pen.setStyle(QtCore.Qt.DashLine)

        new_rect = rect.adjusted(1, 1, -1, -1)
        painter.setPen(pen)
        painter.setBrush(QtCore.Qt.transparent)
        # painter.drawRect(rect)
        painter.drawRect(new_rect)

    def _cache_pix(self):
        rect = self.rect()
        rect_width = rect.width()
        rect_height = rect.height()

        pix_x_offset = 0
        pix_y_offset = 0
        expected_height = int(
            (rect_width / self.width_ratio) * self.height_ratio
        )
        if expected_height > rect_height:
            expected_height = rect_height
            expected_width = int(
                (rect_height / self.height_ratio) * self.width_ratio
            )
            pix_x_offset = (rect_width - expected_width) / 2
        else:
            expected_width = rect_width
            pix_y_offset = (rect_height - expected_height) / 2

        if self._current_pixes is None:
            used_default_pix = True
            pixes_to_draw = None
            pixes_len = 1
        else:
            used_default_pix = False
            pixes_to_draw = self._current_pixes
            if len(pixes_to_draw) > self.max_thumbnails:
                pixes_to_draw = pixes_to_draw[:-self.max_thumbnails]
            pixes_len = len(pixes_to_draw)

        width_offset, height_offset = self._get_pix_offset_size(
            expected_width, expected_height, pixes_len
        )
        pix_width = expected_width - width_offset
        pix_height = expected_height - height_offset

        if used_default_pix:
            thumbnail_images = [self._paint_default_pix(pix_width, pix_height)]
        else:
            thumbnail_images = self._draw_thumbnails(
                pixes_to_draw, pix_width, pix_height
            )

        if pixes_len == 1:
            width_offset_part = 0
            height_offset_part = 0
        else:
            width_offset_part = int(float(width_offset) / (pixes_len - 1))
            height_offset_part = int(float(height_offset) / (pixes_len - 1))
        full_width_offset = width_offset + pix_x_offset

        final_pix = QtGui.QPixmap(rect_width, rect_height)
        final_pix.fill(QtCore.Qt.transparent)

        bg_pen = QtGui.QPen()
        bg_pen.setWidth(self.border_width)
        bg_pen.setColor(self.border_color)

        final_painter = QtGui.QPainter()
        final_painter.begin(final_pix)
        render_hints = (
            QtGui.QPainter.Antialiasing
            | QtGui.QPainter.SmoothPixmapTransform
        )
        if hasattr(QtGui.QPainter, "HighQualityAntialiasing"):
            render_hints |= QtGui.QPainter.HighQualityAntialiasing

        final_painter.setRenderHints(render_hints)

        final_painter.setBrush(QtGui.QBrush(self.thumbnail_bg_color))
        final_painter.setPen(bg_pen)
        final_painter.drawRect(rect)

        for idx, pix in enumerate(thumbnail_images):
            x_offset = full_width_offset - (width_offset_part * idx)
            y_offset = (height_offset_part * idx) + pix_y_offset
            final_painter.drawPixmap(x_offset, y_offset, pix)

        # Draw drop enabled dashes
        if used_default_pix:
            self._paint_dash_line(final_painter, rect)

        final_painter.end()

        self._cached_pix = final_pix

    def _get_pix_offset_size(self, width, height, image_count):
        if image_count == 1:
            return 0, 0

        part_width = width / self.offset_sep
        part_height = height / self.offset_sep
        return part_width, part_height


class ThumbnailWidget(QtWidgets.QWidget):
    """Instance thumbnail widget."""

    thumbnail_created = QtCore.Signal(str)
    thumbnail_cleared = QtCore.Signal()

    def __init__(self, controller, parent):
        # Missing implementation for thumbnail
        # - widget kept to make a visial offset of global attr widget offset
        super(ThumbnailWidget, self).__init__(parent)
        self.setAcceptDrops(True)

        thumbnail_painter = ThumbnailPainterWidget(self)

        buttons_widget = QtWidgets.QWidget(self)
        buttons_widget.setAttribute(QtCore.Qt.WA_TranslucentBackground)

        icon_color = get_objected_colors("bg-view-selection").get_qcolor()
        icon_color.setAlpha(255)

        clear_image = get_image("clear_thumbnail")
        clear_pix = paint_image_with_color(clear_image, icon_color)
        clear_button = PixmapButton(clear_pix, buttons_widget)
        clear_button.setObjectName("ThumbnailPixmapHoverButton")
        clear_button.setToolTip("Clear thumbnail")

        take_screenshot_image = get_image("take_screenshot")
        take_screenshot_pix = paint_image_with_color(
            take_screenshot_image, icon_color)
        take_screenshot_btn = PixmapButton(
            take_screenshot_pix, buttons_widget)
        take_screenshot_btn.setObjectName("ThumbnailPixmapHoverButton")
        take_screenshot_btn.setToolTip("Take screenshot")

        buttons_layout = QtWidgets.QHBoxLayout(buttons_widget)
        buttons_layout.setContentsMargins(3, 3, 3, 3)
        buttons_layout.addStretch(1)
        buttons_layout.addWidget(take_screenshot_btn, 0)
        buttons_layout.addWidget(clear_button, 0)

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(thumbnail_painter)

        clear_button.clicked.connect(self._on_clear_clicked)
        take_screenshot_btn.clicked.connect(self._on_take_screenshot)

        self._controller = controller
        self._output_dir = controller.get_thumbnail_temp_dir_path()

        self._review_extensions = set(IMAGE_EXTENSIONS) | set(VIDEO_EXTENSIONS)

        self._height = None
        self._width = None
        self._adapted_to_size = True
        self._last_width = None
        self._last_height = None

        self._buttons_widget = buttons_widget
        self._thumbnail_painter = thumbnail_painter
        self._clear_button = clear_button
        self._take_screenshot_btn = take_screenshot_btn

    @property
    def width_ratio(self):
        return self._thumbnail_painter.width_ratio

    @property
    def height_ratio(self):
        return self._thumbnail_painter.height_ratio

    def _get_filepath_from_event(self, event):
        mime_data = event.mimeData()
        if not mime_data.hasUrls():
            return None

        filepaths = []
        for url in mime_data.urls():
            filepath = url.toLocalFile()
            if os.path.exists(filepath):
                filepaths.append(filepath)

        if len(filepaths) == 1:
            filepath = filepaths[0]
            ext = os.path.splitext(filepath)[-1]
            if ext in self._review_extensions:
                return filepath
        return None

    def dragEnterEvent(self, event):
        filepath = self._get_filepath_from_event(event)
        if filepath:
            event.setDropAction(QtCore.Qt.CopyAction)
            event.accept()

    def dragLeaveEvent(self, event):
        event.accept()

    def dropEvent(self, event):
        filepath = self._get_filepath_from_event(event)
        if not filepath:
            return

        output = export_thumbnail(filepath, self._output_dir)
        if output:
            self.thumbnail_created.emit(output)
        else:
            self._controller.emit_card_message(
                "Couldn't convert the source for thumbnail",
                CardMessageTypes.error
            )

    def set_adapted_to_hint(self, enabled):
        self._adapted_to_size = enabled
        if self._width is not None:
            self.setMinimumHeight(0)
            self._width = None

        if self._height is not None:
            self.setMinimumWidth(0)
            self._height = None

    def set_width(self, width):
        if self._width == width:
            return

        self._adapted_to_size = False
        self._width = width
        self.setMinimumHeight(int(
            (width / self.width_ratio) * self.height_ratio
        ))
        if self._height is not None:
            self.setMinimumWidth(0)
            self._height = None
        self._thumbnail_painter.clear_cache()

    def set_height(self, height):
        if self._height == height:
            return

        self._height = height
        self._adapted_to_size = False
        self.setMinimumWidth(int(
            (height / self.height_ratio) * self.width_ratio
        ))
        if self._width is not None:
            self.setMinimumHeight(0)
            self._width = None

        self._thumbnail_painter.clear_cache()

    def set_current_thumbnails(self, thumbnail_paths=None):
        self._thumbnail_painter.set_current_thumbnails(thumbnail_paths)
        self._update_buttons_position()

    def _on_clear_clicked(self):
        self.set_current_thumbnails()
        self.thumbnail_cleared.emit()

    def _on_take_screenshot(self):
        output_path = os.path.join(
            self._output_dir, uuid.uuid4().hex + ".png")
        if capture_to_file(output_path):
            self.thumbnail_created.emit(output_path)

    def _adapt_to_size(self):
        if not self._adapted_to_size:
            return

        width = self.width()
        height = self.height()
        if width == self._last_width and height == self._last_height:
            return

        self._last_width = width
        self._last_height = height
        self._thumbnail_painter.clear_cache()

    def _update_buttons_position(self):
        self._clear_button.setVisible(self._thumbnail_painter.has_pixes)
        size = self.size()
        my_height = size.height()
        height = self._buttons_widget.sizeHint().height()
        self._buttons_widget.setGeometry(
            0, my_height - height,
            size.width(), height
        )

    def resizeEvent(self, event):
        super(ThumbnailWidget, self).resizeEvent(event)
        self._adapt_to_size()
        self._update_buttons_position()

    def showEvent(self, event):
        super(ThumbnailWidget, self).showEvent(event)
        self._adapt_to_size()
        self._update_buttons_position()


def _run_silent_subprocess(args):
    with open(os.devnull, "w") as devnull:
        run_subprocess(args, stdout=devnull, stderr=devnull)


def _convert_thumbnail_oiio(src_path, dst_path):
    if not is_oiio_supported():
        return None

    oiio_cmd = get_oiio_tool_args(
        "oiiotool",
        "-i", src_path,
        "--subimage", "0",
        "-o", dst_path
    )
    try:
        _run_silent_subprocess(oiio_cmd)
    except Exception:
        return None
    return dst_path


def _convert_thumbnail_ffmpeg(src_path, dst_path):
    ffmpeg_cmd = get_ffmpeg_tool_args(
        "ffmpeg",
        "-y",
        "-i", src_path,
        dst_path
    )
    try:
        _run_silent_subprocess(ffmpeg_cmd)
    except Exception:
        return None
    return dst_path


def export_thumbnail(src_path, root_dir):
    if not os.path.exists(root_dir):
        os.makedirs(root_dir)

    ext = os.path.splitext(src_path)[-1]
    if ext not in (".jpeg", ".jpg", ".png"):
        ext = ".jpeg"
    filename = str(uuid.uuid4()) + ext
    dst_path = os.path.join(root_dir, filename)

    output_path = _convert_thumbnail_oiio(src_path, dst_path)
    if not output_path:
        output_path = _convert_thumbnail_ffmpeg(src_path, dst_path)
    return output_path
