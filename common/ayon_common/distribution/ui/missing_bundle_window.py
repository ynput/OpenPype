import sys

from qtpy import QtWidgets, QtGui

from ayon_common import is_staging_enabled
from ayon_common.resources import (
    get_icon_path,
    load_stylesheet,
)
from ayon_common.ui_utils import get_qt_app


class MissingBundleWindow(QtWidgets.QDialog):
    default_width = 410
    default_height = 170

    def __init__(
        self, url=None, bundle_name=None, use_staging=None, parent=None
    ):
        super().__init__(parent)

        icon_path = get_icon_path()
        icon = QtGui.QIcon(icon_path)
        self.setWindowIcon(icon)
        self.setWindowTitle("Missing Bundle")

        self._url = url
        self._bundle_name = bundle_name
        self._use_staging = use_staging
        self._first_show = True

        info_label = QtWidgets.QLabel("", self)
        info_label.setWordWrap(True)

        btns_widget = QtWidgets.QWidget(self)
        confirm_btn = QtWidgets.QPushButton("Exit", btns_widget)

        btns_layout = QtWidgets.QHBoxLayout(btns_widget)
        btns_layout.setContentsMargins(0, 0, 0, 0)
        btns_layout.addStretch(1)
        btns_layout.addWidget(confirm_btn, 0)

        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.addWidget(info_label, 0)
        main_layout.addStretch(1)
        main_layout.addWidget(btns_widget, 0)

        confirm_btn.clicked.connect(self._on_confirm_click)

        self._info_label = info_label
        self._confirm_btn = confirm_btn

        self._update_label()

    def set_url(self, url):
        if url == self._url:
            return
        self._url = url
        self._update_label()

    def set_bundle_name(self, bundle_name):
        if bundle_name == self._bundle_name:
            return
        self._bundle_name = bundle_name
        self._update_label()

    def set_use_staging(self, use_staging):
        if self._use_staging == use_staging:
            return
        self._use_staging = use_staging
        self._update_label()

    def showEvent(self, event):
        super().showEvent(event)
        if self._first_show:
            self._first_show = False
            self._on_first_show()
        self._recalculate_sizes()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._recalculate_sizes()

    def _recalculate_sizes(self):
        hint = self._confirm_btn.sizeHint()
        new_width = max((hint.width(), hint.height() * 3))
        self._confirm_btn.setMinimumWidth(new_width)

    def _on_first_show(self):
        self.setStyleSheet(load_stylesheet())
        self.resize(self.default_width, self.default_height)

    def _on_confirm_click(self):
        self.accept()
        self.close()

    def _update_label(self):
        self._info_label.setText(self._get_label())

    def _get_label(self):
        url_part = f" <b>{self._url}</b>" if self._url else ""

        if self._bundle_name:
            return (
                f"Requested release bundle <b>{self._bundle_name}</b>"
                f" is not available on server{url_part}."
                "<br/><br/>Try to restart AYON desktop launcher. Please"
                " contact your administrator if issue persist."
            )
        mode = "staging" if self._use_staging else "production"
        return (
            f"No release bundle is set as {mode} on the AYON"
            f" server{url_part} so there is nothing to launch."
            "<br/><br/>Please contact your administrator"
            " to resolve the issue."
        )


def main():
    """Show message that server does not have set bundle to use.

    It is possible to pass url as argument to show it in the message. To use
        this feature, pass `--url <url>` as argument to this script.
    """

    url = None
    bundle_name = None
    if "--url" in sys.argv:
        url_index = sys.argv.index("--url") + 1
        if url_index < len(sys.argv):
            url = sys.argv[url_index]

    if "--bundle" in sys.argv:
        bundle_index = sys.argv.index("--bundle") + 1
        if bundle_index < len(sys.argv):
            bundle_name = sys.argv[bundle_index]

    use_staging = is_staging_enabled()
    app = get_qt_app()
    window = MissingBundleWindow(url, bundle_name, use_staging)
    window.show()
    app.exec_()


if __name__ == "__main__":
    main()
