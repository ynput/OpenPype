from Qt import QtWidgets

from openpype import style
if __package__:
    from .widgets import PublishReportViewerWidget
else:
    from widgets import PublishReportViewerWidget


class PublishReportViewerWindow(QtWidgets.QWidget):
    # TODO add buttons to be able load report file or paste content of report
    default_width = 1200
    default_height = 600

    def __init__(self, parent=None):
        super(PublishReportViewerWindow, self).__init__(parent)

        main_widget = PublishReportViewerWidget(self)

        layout = QtWidgets.QHBoxLayout(self)
        layout.addWidget(main_widget)

        self._main_widget = main_widget

        self.resize(self.default_width, self.default_height)
        self.setStyleSheet(style.load_stylesheet())

    def set_report(self, report_data):
        self._main_widget.set_report(report_data)
