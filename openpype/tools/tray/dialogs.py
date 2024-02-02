import os

from qtpy import QtWidgets, QtCore, QtGui

from openpype import resources, style
from openpype.tools.utils import (
    paint_image_with_color,
    get_warning_pixmap,
)


class PixmapLabel(QtWidgets.QLabel):
    """Label resizing image to height of font."""
    def __init__(self, pixmap, parent):
        super(PixmapLabel, self).__init__(parent)
        self._empty_pixmap = QtGui.QPixmap(0, 0)
        self._source_pixmap = pixmap

    def set_source_pixmap(self, pixmap):
        """Change source image."""
        self._source_pixmap = pixmap
        self._set_resized_pix()

    def _get_pix_size(self):
        size = self.fontMetrics().height() * 3
        return size, size

    def _set_resized_pix(self):
        if self._source_pixmap is None:
            self.setPixmap(self._empty_pixmap)
            return
        width, height = self._get_pix_size()
        self.setPixmap(
            self._source_pixmap.scaled(
                width,
                height,
                QtCore.Qt.KeepAspectRatio,
                QtCore.Qt.SmoothTransformation
            )
        )

    def resizeEvent(self, event):
        self._set_resized_pix()
        super(PixmapLabel, self).resizeEvent(event)


class VersionUpdateDialog(QtWidgets.QDialog):
    restart_requested = QtCore.Signal()
    ignore_requested = QtCore.Signal()

    _min_width = 400
    _min_height = 130

    def __init__(self, parent=None):
        super(VersionUpdateDialog, self).__init__(parent)

        icon = QtGui.QIcon(resources.get_openpype_icon_filepath())
        self.setWindowIcon(icon)
        self.setWindowFlags(
            self.windowFlags()
            | QtCore.Qt.WindowStaysOnTopHint
        )

        self.setMinimumWidth(self._min_width)
        self.setMinimumHeight(self._min_height)

        top_widget = QtWidgets.QWidget(self)

        gift_pixmap = self._get_gift_pixmap()
        gift_icon_label = PixmapLabel(gift_pixmap, top_widget)

        label_widget = QtWidgets.QLabel(top_widget)
        label_widget.setWordWrap(True)

        top_layout = QtWidgets.QHBoxLayout(top_widget)
        top_layout.setSpacing(10)
        top_layout.addWidget(gift_icon_label, 0, QtCore.Qt.AlignCenter)
        top_layout.addWidget(label_widget, 1)

        ignore_btn = QtWidgets.QPushButton(self)
        restart_btn = QtWidgets.QPushButton("Restart && Change", self)
        restart_btn.setObjectName("TrayRestartButton")

        btns_layout = QtWidgets.QHBoxLayout()
        btns_layout.addStretch(1)
        btns_layout.addWidget(ignore_btn, 0)
        btns_layout.addWidget(restart_btn, 0)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(top_widget, 0)
        layout.addStretch(1)
        layout.addLayout(btns_layout, 0)

        ignore_btn.clicked.connect(self._on_ignore)
        restart_btn.clicked.connect(self._on_reset)

        self._label_widget = label_widget
        self._gift_icon_label = gift_icon_label
        self._ignore_btn = ignore_btn
        self._restart_btn = restart_btn

        self._restart_accepted = False
        self._current_is_higher = False

        self.setStyleSheet(style.load_stylesheet())

    def _get_gift_pixmap(self):
        image_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "images",
            "gifts.png"
        )
        src_image = QtGui.QImage(image_path)
        color_value = style.get_objected_colors("font")

        return paint_image_with_color(
            src_image,
            color_value.get_qcolor()
        )

    def showEvent(self, event):
        super(VersionUpdateDialog, self).showEvent(event)
        self._restart_accepted = False

    def closeEvent(self, event):
        super(VersionUpdateDialog, self).closeEvent(event)
        if self._restart_accepted or self._current_is_higher:
            return
        # Trigger ignore requested only if restart was not clicked and current
        #   version is lower
        self.ignore_requested.emit()

    def update_versions(
        self, current_version, expected_version, current_is_higher
    ):
        if not current_is_higher:
            title = "OpenPype update is needed"
            label_message = (
                "Running OpenPype version is <b>{}</b>."
                " Your production has been updated to version <b>{}</b>."
            ).format(str(current_version), str(expected_version))
            ignore_label = "Later"

        else:
            title = "OpenPype version is higher"
            label_message = (
                "Running OpenPype version is <b>{}</b>."
                " Your production uses version <b>{}</b>."
            ).format(str(current_version), str(expected_version))
            ignore_label = "Ignore"

        self.setWindowTitle(title)

        self._current_is_higher = current_is_higher

        self._gift_icon_label.setVisible(not current_is_higher)

        self._label_widget.setText(label_message)
        self._ignore_btn.setText(ignore_label)

    def _on_ignore(self):
        self.reject()

    def _on_reset(self):
        self._restart_accepted = True
        self.restart_requested.emit()
        self.accept()


class ProductionStagingDialog(QtWidgets.QDialog):
    """Tell user that he has enabled staging but is in production version.

    This is showed only when staging is enabled with '--use-staging' and it's
    version is the same as production's version.
    """

    def __init__(self, parent=None):
        super(ProductionStagingDialog, self).__init__(parent)

        icon = QtGui.QIcon(resources.get_openpype_icon_filepath())
        self.setWindowIcon(icon)
        self.setWindowTitle("Production and Staging versions are the same")
        self.setWindowFlags(
            self.windowFlags()
            | QtCore.Qt.WindowStaysOnTopHint
        )

        top_widget = QtWidgets.QWidget(self)

        staging_pixmap = QtGui.QPixmap(
            resources.get_openpype_staging_icon_filepath()
        )
        staging_icon_label = PixmapLabel(staging_pixmap, top_widget)
        message = (
            "Because production and staging versions are the same"
            " your changes and work will affect both."
        )
        content_label = QtWidgets.QLabel(message, self)
        content_label.setWordWrap(True)

        top_layout = QtWidgets.QHBoxLayout(top_widget)
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.setSpacing(10)
        top_layout.addWidget(
            staging_icon_label, 0,
            QtCore.Qt.AlignTop | QtCore.Qt.AlignHCenter
        )
        top_layout.addWidget(content_label, 1)

        footer_widget = QtWidgets.QWidget(self)
        ok_btn = QtWidgets.QPushButton("I understand", footer_widget)

        footer_layout = QtWidgets.QHBoxLayout(footer_widget)
        footer_layout.setContentsMargins(0, 0, 0, 0)
        footer_layout.addStretch(1)
        footer_layout.addWidget(ok_btn)

        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.addWidget(top_widget, 0)
        main_layout.addStretch(1)
        main_layout.addWidget(footer_widget, 0)

        self.setStyleSheet(style.load_stylesheet())
        self.resize(400, 140)

        ok_btn.clicked.connect(self._on_ok_clicked)

    def _on_ok_clicked(self):
        self.close()


class BuildVersionDialog(QtWidgets.QDialog):
    """Build/Installation version is too low for current OpenPype version.

    This dialog tells to user that it's build OpenPype is too old.
    """
    def __init__(self, parent=None):
        super(BuildVersionDialog, self).__init__(parent)

        icon = QtGui.QIcon(resources.get_openpype_icon_filepath())
        self.setWindowIcon(icon)
        self.setWindowTitle("Outdated OpenPype installation")
        self.setWindowFlags(
            self.windowFlags()
            | QtCore.Qt.WindowStaysOnTopHint
        )

        top_widget = QtWidgets.QWidget(self)

        warning_pixmap = get_warning_pixmap()
        warning_icon_label = PixmapLabel(warning_pixmap, top_widget)

        message = (
            "Your installation of OpenPype <b>does not match minimum"
            " requirements</b>.<br/><br/>Please update OpenPype installation"
            " to newer version."
        )
        content_label = QtWidgets.QLabel(message, self)

        top_layout = QtWidgets.QHBoxLayout(top_widget)
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.addWidget(
            warning_icon_label, 0,
            QtCore.Qt.AlignTop | QtCore.Qt.AlignHCenter
        )
        top_layout.addWidget(content_label, 1)

        footer_widget = QtWidgets.QWidget(self)
        ok_btn = QtWidgets.QPushButton("I understand", footer_widget)

        footer_layout = QtWidgets.QHBoxLayout(footer_widget)
        footer_layout.setContentsMargins(0, 0, 0, 0)
        footer_layout.addStretch(1)
        footer_layout.addWidget(ok_btn)

        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.addWidget(top_widget, 0)
        main_layout.addStretch(1)
        main_layout.addWidget(footer_widget, 0)

        self.setStyleSheet(style.load_stylesheet())

        ok_btn.clicked.connect(self._on_ok_clicked)

    def _on_ok_clicked(self):
        self.close()
