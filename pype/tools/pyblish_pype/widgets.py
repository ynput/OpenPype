import sys
from Qt import QtCore, QtWidgets, QtGui
from . import model, delegate, view, awesome
from .constants import PluginStates, InstanceStates, Roles


class EllidableLabel(QtWidgets.QLabel):
    def __init__(self, *args, **kwargs):
        super(self.__class__, self).__init__(*args, **kwargs)
        self.setObjectName("EllidableLabel")

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)

        metrics = QtGui.QFontMetrics(self.font())
        elided = metrics.elidedText(
            self.text(), QtCore.Qt.ElideRight, self.width()
        )
        painter.drawText(self.rect(), self.alignment(), elided)


class PerspectiveLabel(QtWidgets.QTextEdit):
    def __init__(self, parent=None):
        super(self.__class__, self).__init__(parent)
        self.setObjectName("PerspectiveLabel")

        size_policy = self.sizePolicy()
        size_policy.setHeightForWidth(True)
        size_policy.setVerticalPolicy(QtWidgets.QSizePolicy.Preferred)
        self.setSizePolicy(size_policy)

        self.textChanged.connect(self.on_text_changed)

    def on_text_changed(self, *args, **kwargs):
        self.updateGeometry()

    def hasHeightForWidth(self):
        return True

    def heightForWidth(self, width):
        margins = self.contentsMargins()

        document_width = 0
        if width >= margins.left() + margins.right():
            document_width = width - margins.left() - margins.right()

        document = self.document().clone()
        document.setTextWidth(document_width)

        return margins.top() + document.size().height() + margins.bottom()

    def sizeHint(self):
        width = super(self.__class__, self).sizeHint().width()
        return QtCore.QSize(width, self.heightForWidth(width))


class PerspectiveWidget(QtWidgets.QWidget):
    l_doc = "Documentation"
    l_rec = "Records"
    l_path = "Path"

    def __init__(self, parent):
        super(PerspectiveWidget, self).__init__(parent)

        self.parent_widget = parent
        main_layout = QtWidgets.QVBoxLayout(self)

        header_widget = QtWidgets.QWidget()
        toggle_button = QtWidgets.QPushButton(parent=header_widget)
        toggle_button.setObjectName("PerspectiveToggleBtn")
        toggle_button.setText(delegate.icons["angle-left"])
        toggle_button.setMinimumHeight(50)
        toggle_button.setFixedWidth(40)

        indicator = QtWidgets.QLabel("", parent=header_widget)
        indicator.setFixedWidth(30)
        indicator.setAlignment(QtCore.Qt.AlignCenter)
        indicator.setObjectName("PerspectiveIndicator")

        name = EllidableLabel('*Name of inspected', parent=header_widget)

        header_layout = QtWidgets.QHBoxLayout(header_widget)
        header_layout.setAlignment(QtCore.Qt.AlignLeft)
        header_layout.addWidget(toggle_button)
        header_layout.addWidget(indicator)
        header_layout.addWidget(name)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(10)
        header_widget.setLayout(header_layout)

        main_layout.setAlignment(QtCore.Qt.AlignTop)
        main_layout.addWidget(header_widget)

        scroll_widget = QtWidgets.QScrollArea(self)
        scroll_widget.setObjectName("PerspectiveScrollContent")

        contents_widget = QtWidgets.QWidget(scroll_widget)
        contents_widget.setObjectName("PerspectiveWidgetContent")

        layout = QtWidgets.QVBoxLayout()
        layout.setAlignment(QtCore.Qt.AlignTop)
        layout.setContentsMargins(0, 0, 0, 0)

        documentation = ExpandableWidget(self, self.l_doc)
        doc_label = PerspectiveLabel()
        documentation.set_content(doc_label)
        layout.addWidget(documentation)

        path = ExpandableWidget(self, self.l_path)
        path_label = PerspectiveLabel()
        path.set_content(path_label)
        layout.addWidget(path)

        records = ExpandableWidget(self, self.l_rec)
        layout.addWidget(records)

        contents_widget.setLayout(layout)

        terminal_view = view.TerminalView()
        terminal_view.setObjectName("TerminalView")
        terminal_model = model.TerminalModel()
        terminal_proxy = model.TerminalProxy(terminal_view)
        terminal_proxy.setSourceModel(terminal_model)

        terminal_view.setModel(terminal_proxy)
        terminal_delegate = delegate.TerminalItem()
        terminal_view.setItemDelegate(terminal_delegate)
        records.set_content(terminal_view)

        scroll_widget.setWidgetResizable(True)
        scroll_widget.setWidget(contents_widget)

        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        main_layout.addWidget(scroll_widget)
        self.setLayout(main_layout)

        self.terminal_view = terminal_view
        self.terminal_model = terminal_model
        self.terminal_proxy = terminal_proxy

        self.indicator = indicator
        self.scroll_widget = scroll_widget
        self.contents_widget = contents_widget
        self.toggle_button = toggle_button
        self.name_widget = name
        self.documentation = documentation
        self.path = path
        self.records = records

        self.toggle_button.clicked.connect(self.toggle_me)

        self.last_type = None
        self.last_item_id = None
        self.last_id = None

    def trim(self, docstring):
        if not docstring:
            return ""
        # Convert tabs to spaces (following the normal Python rules)
        # and split into a list of lines:
        lines = docstring.expandtabs().splitlines()
        # Determine minimum indentation (first line doesn't count):
        try:
            indent = sys.maxint
            max = sys.maxint
        except Exception:
            indent = sys.maxsize
            max = sys.maxsize

        for line in lines[1:]:
            stripped = line.lstrip()
            if stripped:
                indent = min(indent, len(line) - len(stripped))
        # Remove indentation (first line is special):
        trimmed = [lines[0].strip()]
        if indent < max:
            for line in lines[1:]:
                trimmed.append(line[indent:].rstrip())
        # Strip off trailing and leading blank lines:
        while trimmed and not trimmed[-1]:
            trimmed.pop()
        while trimmed and not trimmed[0]:
            trimmed.pop(0)
        # Return a single string:
        return "\n".join(trimmed)

    def set_indicator_state(self, state):
        self.indicator.setProperty("state", state)
        self.indicator.style().polish(self.indicator)

    def reset(self):
        self.last_id = None
        self.set_records(list())
        self.set_indicator_state(None)

    def update_context(self, plugin_item, instance_item):
        if not self.last_item_id or not self.last_type:
            return

        if self.last_type == model.PluginType:
            if not self.last_id:
                _item_id = plugin_item.data(Roles.ObjectUIdRole)
                if _item_id != self.last_item_id:
                    return
                self.last_id = plugin_item.plugin.id

            elif self.last_id != plugin_item.plugin.id:
                return

            self.set_context(plugin_item.index())
            return

        if self.last_type == model.InstanceType:
            if not self.last_id:
                _item_id = instance_item.data(Roles.ObjectUIdRole)
                if _item_id != self.last_item_id:
                    return
                self.last_id = instance_item.instance.id

            elif self.last_id != instance_item.instance.id:
                return

            self.set_context(instance_item.index())
            return

    def set_context(self, index):
        if not index or not index.isValid():
            index_type = None
        else:
            index_type = index.data(Roles.TypeRole)

        if index_type == model.InstanceType:
            item_id = index.data(Roles.ObjectIdRole)
            publish_states = index.data(Roles.PublishFlagsRole)
            if publish_states & InstanceStates.ContextType:
                type_indicator = "C"
            else:
                type_indicator = "I"

            if publish_states & InstanceStates.InProgress:
                self.set_indicator_state("active")

            elif publish_states & InstanceStates.HasError:
                self.set_indicator_state("error")

            elif publish_states & InstanceStates.HasWarning:
                self.set_indicator_state("warning")

            elif publish_states & InstanceStates.HasFinished:
                self.set_indicator_state("ok")
            else:
                self.set_indicator_state(None)

            self.documentation.setVisible(False)
            self.path.setVisible(False)

        elif index_type == model.PluginType:
            item_id = index.data(Roles.ObjectIdRole)
            type_indicator = "P"

            doc = index.data(Roles.DocstringRole)
            doc_str = ""
            if doc:
                doc_str = self.trim(doc)

            publish_states = index.data(Roles.PublishFlagsRole)
            if publish_states & PluginStates.InProgress:
                self.set_indicator_state("active")

            elif publish_states & PluginStates.HasError:
                self.set_indicator_state("error")

            elif publish_states & PluginStates.HasWarning:
                self.set_indicator_state("warning")

            elif publish_states & PluginStates.WasProcessed:
                self.set_indicator_state("ok")

            else:
                self.set_indicator_state(None)

            self.documentation.toggle_content(bool(doc_str))
            self.documentation.content.setText(doc_str)

            path = index.data(Roles.PathModuleRole) or ""
            self.path.toggle_content(path.strip() != "")
            self.path.content.setText(path)

            self.documentation.setVisible(True)
            self.path.setVisible(True)

        else:
            self.last_type = None
            self.last_id = None
            self.indicator.setText("?")
            self.set_indicator_state(None)
            self.documentation.setVisible(False)
            self.path.setVisible(False)
            self.records.setVisible(False)
            return

        self.last_type = index_type
        self.last_id = item_id
        self.last_item_id = index.data(Roles.ObjectUIdRole)

        self.indicator.setText(type_indicator)

        label = index.data(QtCore.Qt.DisplayRole)
        self.name_widget.setText(label)
        self.records.setVisible(True)

        records = index.data(Roles.LogRecordsRole) or []
        self.set_records(records)

    def set_records(self, records):
        len_records = 0
        if records:
            len_records += len(records)

        data = {"records": records}
        self.terminal_model.reset()
        self.terminal_model.update_with_result(data)

        self.records.button_toggle_text.setText(
            "{} ({})".format(self.l_rec, len_records)
        )
        self.records.toggle_content(len_records > 0)

    def toggle_me(self):
        self.parent_widget.toggle_perspective_widget()


class ClickableWidget(QtWidgets.QLabel):
    clicked = QtCore.Signal()

    def mouseReleaseEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            self.clicked.emit()
        super(ClickableWidget, self).mouseReleaseEvent(event)


class ExpandableWidget(QtWidgets.QWidget):

    content = None

    def __init__(self, parent, title):
        super(ExpandableWidget, self).__init__(parent)

        top_part = ClickableWidget(parent=self)
        top_part.setObjectName("ExpandableHeader")

        button_size = QtCore.QSize(5, 5)
        button_toggle = QtWidgets.QToolButton(parent=top_part)
        button_toggle.setIconSize(button_size)
        button_toggle.setArrowType(QtCore.Qt.RightArrow)
        button_toggle.setCheckable(True)
        button_toggle.setChecked(False)

        button_toggle_text = QtWidgets.QLabel(title, parent=top_part)

        layout = QtWidgets.QHBoxLayout(top_part)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)
        layout.addWidget(button_toggle)
        layout.addWidget(button_toggle_text)
        top_part.setLayout(layout)

        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(9, 9, 9, 0)

        content = QtWidgets.QFrame(self)
        content.setObjectName("ExpandableWidgetContent")
        content.setVisible(False)

        content_layout = QtWidgets.QVBoxLayout(content)

        main_layout.addWidget(top_part)
        main_layout.addWidget(content)
        self.setLayout(main_layout)

        self.setAttribute(QtCore.Qt.WA_StyledBackground)

        self.top_part = top_part
        self.button_toggle = button_toggle
        self.button_toggle_text = button_toggle_text

        self.content_widget = content
        self.content_layout = content_layout

        self.top_part.clicked.connect(self.top_part_clicked)
        self.button_toggle.clicked.connect(self.toggle_content)

    def top_part_clicked(self):
        self.toggle_content(not self.button_toggle.isChecked())

    def toggle_content(self, *args):
        if len(args) > 0:
            checked = args[0]
        else:
            checked = self.button_toggle.isChecked()
        arrow_type = QtCore.Qt.RightArrow
        if checked:
            arrow_type = QtCore.Qt.DownArrow
        self.button_toggle.setChecked(checked)
        self.button_toggle.setArrowType(arrow_type)
        self.content_widget.setVisible(checked)

    def resizeEvent(self, event):
        super(self.__class__, self).resizeEvent(event)
        self.content.updateGeometry()

    def set_content(self, in_widget):
        if self.content:
            self.content.hide()
            self.content_layout.removeWidget(self.content)
        self.content_layout.addWidget(in_widget)
        self.content = in_widget


class ButtonWithMenu(QtWidgets.QWidget):
    def __init__(self, button_title, parent=None):
        super(ButtonWithMenu, self).__init__(parent=parent)
        self.setSizePolicy(QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Maximum, QtWidgets.QSizePolicy.Maximum
        ))

        self.layout = QtWidgets.QHBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)

        self.menu = QtWidgets.QMenu()
        # TODO move to stylesheets
        self.menu.setStyleSheet("""
            *{color: #fff; background-color: #555; border: 1px solid #222;}
            ::item {background-color: transparent;padding: 5px;
            padding-left: 10px;padding-right: 10px;}
            ::item:selected {background-color: #666;}
        """)

        self.button = QtWidgets.QPushButton(button_title)
        self.button.setObjectName("ButtonWithMenu")

        self.layout.addWidget(self.button)

        self.button.clicked.connect(self.btn_clicked)

    def btn_clicked(self):
        self.menu.popup(self.button.mapToGlobal(
            QtCore.QPoint(0, self.button.height())
        ))

    def addItem(self, text, callback):
        self.menu.addAction(text, callback)
        self.button.setToolTip("Select to apply predefined presets")

    def clearMenu(self):
        self.menu.clear()
        self.button.setToolTip("Presets not found")


class CommentBox(QtWidgets.QLineEdit):

    def __init__(self, placeholder_text, parent=None):
        super(CommentBox, self).__init__(parent=parent)
        self.placeholder = QtWidgets.QLabel(placeholder_text, self)
        self.placeholder.move(2, 2)

    def focusInEvent(self, event):
        self.placeholder.setVisible(False)
        return super(CommentBox, self).focusInEvent(event)

    def focusOutEvent(self, event):
        current_text = self.text()
        current_text = current_text.strip(" ")
        self.setText(current_text)
        if not self.text():
            self.placeholder.setVisible(True)
        return super(CommentBox, self).focusOutEvent(event)


class TerminalDetail(QtWidgets.QTextEdit):
    def __init__(self, text, *args, **kwargs):
        super(self.__class__, self).__init__(*args, **kwargs)

        self.setReadOnly(True)
        self.setHtml(text)
        self.setTextInteractionFlags(QtCore.Qt.TextBrowserInteraction)
        self.setWordWrapMode(
            QtGui.QTextOption.WrapAtWordBoundaryOrAnywhere
        )

    def sizeHint(self):
        content_margins = (
            self.contentsMargins().top()
            + self.contentsMargins().bottom()
        )
        size = self.document().documentLayout().documentSize().toSize()
        size.setHeight(size.height() + content_margins)
        return size


class FilterButton(QtWidgets.QPushButton):
    def __init__(self, name, *args, **kwargs):
        self.filter_name = name

        super(self.__class__, self).__init__(*args, **kwargs)

        self.toggled.connect(self.on_toggle)

        self.setProperty("type", name)
        self.setObjectName("TerminalFilerBtn")
        self.setCheckable(True)
        self.setChecked(
            model.TerminalProxy.filter_buttons_checks[name]
        )

    def on_toggle(self, toggle_state):
        model.TerminalProxy.change_filter(self.filter_name, toggle_state)


class TerminalFilterWidget(QtWidgets.QWidget):
    # timer.timeout.connect(lambda: self._update(self.parent_widget))
    def __init__(self, *args, **kwargs):
        super(self.__class__, self).__init__(*args, **kwargs)

        self.filter_changed = QtCore.Signal()

        info_icon = awesome.tags["info"]
        log_icon = awesome.tags["circle"]
        error_icon = awesome.tags["exclamation-triangle"]

        filter_buttons = (
            FilterButton("info", info_icon),
            FilterButton("log_debug", log_icon),
            FilterButton("log_info", log_icon),
            FilterButton("log_warning", log_icon),
            FilterButton("log_error", log_icon),
            FilterButton("log_critical", log_icon),
            FilterButton("error", error_icon)
        )

        layout = QtWidgets.QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        # Add spacers
        layout.addWidget(QtWidgets.QWidget(), 1)

        for btn in filter_buttons:
            layout.addWidget(btn)

        self.setLayout(layout)

        self.filter_buttons = filter_buttons
