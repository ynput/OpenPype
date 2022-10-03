import qtawesome
from Qt import QtWidgets, QtCore, QtGui

from openpype.tools.utils import ClickableFrame


class HelpButton(ClickableFrame):
    resized = QtCore.Signal(int)
    question_mark_icon_name = "fa.question"
    help_icon_name = "fa.question-circle"
    hide_icon_name = "fa.angle-left"

    def __init__(self, *args, **kwargs):
        super(HelpButton, self).__init__(*args, **kwargs)
        self.setObjectName("CreateDialogHelpButton")

        question_mark_label = QtWidgets.QLabel(self)
        help_widget = QtWidgets.QWidget(self)

        help_question = QtWidgets.QLabel(help_widget)
        help_label = QtWidgets.QLabel("Help", help_widget)
        hide_icon = QtWidgets.QLabel(help_widget)

        help_layout = QtWidgets.QHBoxLayout(help_widget)
        help_layout.setContentsMargins(0, 0, 5, 0)
        help_layout.addWidget(help_question, 0)
        help_layout.addWidget(help_label, 0)
        help_layout.addStretch(1)
        help_layout.addWidget(hide_icon, 0)

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(question_mark_label, 0)
        layout.addWidget(help_widget, 1)

        help_widget.setVisible(False)

        self._question_mark_label = question_mark_label
        self._help_widget = help_widget
        self._help_question = help_question
        self._hide_icon = hide_icon

        self._expanded = None
        self.set_expanded()

    def set_expanded(self, expanded=None):
        if self._expanded is expanded:
            if expanded is not None:
                return
            expanded = False
        self._expanded = expanded
        self._help_widget.setVisible(expanded)
        self._update_content()

    def _update_content(self):
        width = self.get_icon_width()
        if self._expanded:
            question_mark_pix = QtGui.QPixmap(width, width)
            question_mark_pix.fill(QtCore.Qt.transparent)

        else:
            question_mark_icon = qtawesome.icon(
                self.question_mark_icon_name, color=QtCore.Qt.white
            )
            question_mark_pix = question_mark_icon.pixmap(width, width)

        hide_icon = qtawesome.icon(
            self.hide_icon_name, color=QtCore.Qt.white
        )
        help_question_icon = qtawesome.icon(
            self.help_icon_name, color=QtCore.Qt.white
        )
        self._question_mark_label.setPixmap(question_mark_pix)
        self._question_mark_label.setMaximumWidth(width)
        self._hide_icon.setPixmap(hide_icon.pixmap(width, width))
        self._help_question.setPixmap(help_question_icon.pixmap(width, width))

    def get_icon_width(self):
        metrics = self.fontMetrics()
        return metrics.height()

    def set_pos_and_size(self, pos_x, pos_y, width, height):
        update_icon = self.height() != height
        self.move(pos_x, pos_y)
        self.resize(width, height)

        if update_icon:
            self._update_content()
            self.updateGeometry()

    def showEvent(self, event):
        super(HelpButton, self).showEvent(event)
        self.resized.emit(self.height())

    def resizeEvent(self, event):
        super(HelpButton, self).resizeEvent(event)
        self.resized.emit(self.height())
