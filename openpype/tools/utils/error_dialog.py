from Qt import QtWidgets, QtCore

from .widgets import ClickableFrame, ExpandBtn


def convert_text_for_html(text):
    return (
        text
        .replace("<", "&#60;")
        .replace(">", "&#62;")
        .replace("\n", "<br>")
        .replace(" ", "&nbsp;")
    )


class TracebackWidget(QtWidgets.QWidget):
    def __init__(self, tb_text, parent):
        super(TracebackWidget, self).__init__(parent)

        # Modify text to match html
        # - add more replacements when needed
        tb_text = convert_text_for_html(tb_text)
        expand_btn = ExpandBtn(self)

        clickable_frame = ClickableFrame(self)
        clickable_layout = QtWidgets.QHBoxLayout(clickable_frame)
        clickable_layout.setContentsMargins(0, 0, 0, 0)

        expand_label = QtWidgets.QLabel("Details", clickable_frame)
        clickable_layout.addWidget(expand_label, 0)
        clickable_layout.addStretch(1)

        show_details_layout = QtWidgets.QHBoxLayout()
        show_details_layout.addWidget(expand_btn, 0)
        show_details_layout.addWidget(clickable_frame, 1)

        text_widget = QtWidgets.QLabel(self)
        text_widget.setText(tb_text)
        text_widget.setTextInteractionFlags(QtCore.Qt.TextBrowserInteraction)
        text_widget.setVisible(False)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addLayout(show_details_layout, 0)
        layout.addWidget(text_widget, 1)

        clickable_frame.clicked.connect(self._on_show_details_click)
        expand_btn.clicked.connect(self._on_show_details_click)

        self._expand_btn = expand_btn
        self._text_widget = text_widget

    def _on_show_details_click(self):
        self._text_widget.setVisible(not self._text_widget.isVisible())
        self._expand_btn.set_collapsed(not self._text_widget.isVisible())


class ErrorMessageBox(QtWidgets.QDialog):
    _default_width = 660
    _default_height = 350

    def __init__(self, title, parent):
        super(ErrorMessageBox, self).__init__(parent)
        self.setWindowTitle(title)
        self.setFocusPolicy(QtCore.Qt.StrongFocus)

        top_widget = self._create_top_widget(self)

        content_scroll = QtWidgets.QScrollArea(self)
        content_scroll.setWidgetResizable(True)

        content_widget = QtWidgets.QWidget(content_scroll)
        content_scroll.setWidget(content_widget)

        content_layout = QtWidgets.QVBoxLayout(content_widget)
        content_layout.setContentsMargins(0, 0, 0, 0)

        # Store content widget before creation of content
        self._content_widget = content_widget

        self._create_content(content_layout)

        content_layout.addStretch(1)

        copy_report_btn = QtWidgets.QPushButton("Copy report", self)
        ok_btn = QtWidgets.QPushButton("OK", self)

        footer_layout = QtWidgets.QHBoxLayout()
        footer_layout.addWidget(copy_report_btn, 0)
        footer_layout.addStretch(1)
        footer_layout.addWidget(ok_btn, 0)

        bottom_line = self._create_line()
        body_layout = QtWidgets.QVBoxLayout(self)
        body_layout.addWidget(top_widget, 0)
        body_layout.addWidget(content_scroll, 1)
        body_layout.addWidget(bottom_line, 0)
        body_layout.addLayout(footer_layout, 0)

        copy_report_btn.clicked.connect(self._on_copy_report)
        ok_btn.clicked.connect(self._on_ok_clicked)

        self.resize(self._default_width, self._default_height)

        report_data = self._get_report_data()
        if not report_data:
            copy_report_btn.setVisible(False)

        self._report_data = report_data

    @staticmethod
    def convert_text_for_html(text):
        return convert_text_for_html(text)

    def _create_top_widget(self, parent_widget):
        label_widget = QtWidgets.QLabel(parent_widget)
        label_widget.setText(
            "<span style='font-size:18pt;'>Something went wrong</span>"
        )
        return label_widget

    def _create_content(self, content_layout):
        raise NotImplementedError(
            "Method '_fill_content_layout' is not implemented!"
        )

    def _get_report_data(self):
        return []

    def _on_ok_clicked(self):
        self.close()

    def _on_copy_report(self):
        report_text = (10 * "*").join(self._report_data)

        mime_data = QtCore.QMimeData()
        mime_data.setText(report_text)
        QtWidgets.QApplication.instance().clipboard().setMimeData(
            mime_data
        )

    def _create_line(self):
        line = QtWidgets.QFrame(self)
        line.setObjectName("Separator")
        line.setMinimumHeight(2)
        line.setMaximumHeight(2)
        return line

    def _create_traceback_widget(self, traceback_text, parent=None):
        if parent is None:
            parent = self._content_widget
        return TracebackWidget(traceback_text, parent)
