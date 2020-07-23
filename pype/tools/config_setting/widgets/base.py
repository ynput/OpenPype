import os
import json
from Qt import QtWidgets, QtCore, QtGui
from . import config
from .lib import NOT_SET
from avalon import io


class TypeToKlass:
    types = {}


class PypeConfigurationWidget:
    is_group = False
    is_overriden = False
    is_modified = False

    def config_value(self):
        raise NotImplementedError(
            "Method `config_value` is not implemented for `{}`.".format(
                self.__class__.__name__
            )
        )

    def value_from_values(self, values, keys=None):
        if not values:
            return NOT_SET

        if keys is None:
            keys = self.keys

        value = values
        for key in keys:
            if not isinstance(value, dict):
                raise TypeError(
                    "Expected dictionary got {}.".format(str(type(value)))
                )

            if key not in value:
                return NOT_SET
            value = value[key]
        return value

    def add_children_gui(self, child_configuration, values):
        raise NotImplementedError((
            "Method `add_children_gui` is not implemented for `{}`."
        ).format(self.__class__.__name__))


class StudioWidget(QtWidgets.QWidget, PypeConfigurationWidget):
    config_dir = os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        "config_gui_schema"
    )
    is_overidable = False

    def __init__(self, parent=None):
        super(StudioWidget, self).__init__(parent)

        self.input_fields = []

        scroll_widget = QtWidgets.QScrollArea(self)
        content_widget = QtWidgets.QWidget(scroll_widget)
        content_layout = QtWidgets.QVBoxLayout(content_widget)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)
        content_layout.setAlignment(QtCore.Qt.AlignTop)
        content_widget.setLayout(content_layout)

        # scroll_widget.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        # scroll_widget.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOn)
        scroll_widget.setWidgetResizable(True)
        scroll_widget.setWidget(content_widget)

        self.scroll_widget = scroll_widget
        self.content_layout = content_layout
        self.content_widget = content_widget

        values = {"studio": config.studio_presets()}
        schema = config.gui_schema("studio_gui_schema")
        self.keys = schema.get("keys", [])
        self.add_children_gui(schema, values)

        footer_widget = QtWidgets.QWidget()
        footer_layout = QtWidgets.QHBoxLayout(footer_widget)

        btn = QtWidgets.QPushButton("Finish")
        spacer_widget = QtWidgets.QWidget()
        footer_layout.addWidget(spacer_widget, 1)
        footer_layout.addWidget(btn, 0)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.setLayout(layout)

        layout.addWidget(scroll_widget, 1)
        layout.addWidget(footer_widget, 0)

        btn.clicked.connect(self.___finish)

    def ___finish(self):
        output = {}
        for item in self.input_fields:
            output.update(item.config_value())

        for key in reversed(self.keys):
            _output = {key: output}
            output = _output

        print(json.dumps(output, indent=4))

    def add_children_gui(self, child_configuration, values):
        item_type = child_configuration["type"]
        klass = TypeToKlass.types.get(item_type)
        item = klass(
            child_configuration, values, self.keys, self
        )
        self.input_fields.append(item)
        self.content_layout.addWidget(item)


class ProjectListWidget(QtWidgets.QWidget):
    default = "< Default >"

    def __init__(self, parent=None):
        super(ProjectListWidget, self).__init__(parent)

        label = QtWidgets.QLabel("Project")
        project_list = QtWidgets.QListView(self)
        project_list.setModel(QtGui.QStandardItemModel())

        layout = QtWidgets.QVBoxLayout(self)
        # content_margin = 5
        # layout.setContentsMargins(
        #     content_margin,
        #     content_margin,
        #     content_margin,
        #     content_margin
        # )
        # layout.setSpacing(3)
        layout.addWidget(label, 0)
        layout.addWidget(project_list, 1)

        self.project_list = project_list

        self.refresh()

    def project_name(self):
        current_selection = self.project_list.currentText()
        if current_selection == self.default:
            return None
        return current_selection

    def refresh(self):
        selected_project = None
        for index in self.project_list.selectedIndexes():
            selected_project = index.data(QtCore.Qt.DisplayRole)
            break

        model = self.project_list.model()
        model.clear()
        items = [self.default]
        io.install()
        for project_doc in tuple(io.projects()):
            print(project_doc["name"])
            items.append(project_doc["name"])

        for item in items:
            model.appendRow(QtGui.QStandardItem(item))

        if not selected_project:
            selected_project = self.default

        found_items = model.findItems(selected_project)
        if found_items:
            index = model.indexFromItem(found_items[0])
            c = QtCore.QItemSelectionModel.SelectionFlag.SelectCurrent
            self.project_list.selectionModel().select(
                index, c
            )
            # self.project_list.selectionModel().setCurrentIndex(
            #     index, c
            # )


class ProjectWidget(QtWidgets.QWidget, PypeConfigurationWidget):
    config_dir = os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        "config_gui_schema"
    )
    is_overidable = True

    def __init__(self, parent=None):
        super(ProjectWidget, self).__init__(parent)

        self.input_fields = []

        scroll_widget = QtWidgets.QScrollArea(self)
        content_widget = QtWidgets.QWidget(scroll_widget)
        content_layout = QtWidgets.QVBoxLayout(content_widget)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)
        content_layout.setAlignment(QtCore.Qt.AlignTop)
        content_widget.setLayout(content_layout)

        scroll_widget.setWidgetResizable(True)
        scroll_widget.setWidget(content_widget)

        project_list_widget = ProjectListWidget()
        content_layout.addWidget(project_list_widget)

        self.project_list_widget = project_list_widget
        self.scroll_widget = scroll_widget
        self.content_layout = content_layout
        self.content_widget = content_widget

        values = config.project_presets()
        schema = config.gui_schema("project_gui_schema")
        self.keys = schema.get("keys", [])
        self.add_children_gui(schema, values)

        footer_widget = QtWidgets.QWidget()
        footer_layout = QtWidgets.QHBoxLayout(footer_widget)

        btn = QtWidgets.QPushButton("Finish")
        spacer_widget = QtWidgets.QWidget()
        footer_layout.addWidget(spacer_widget, 1)
        footer_layout.addWidget(btn, 0)

        presets_widget = QtWidgets.QWidget()
        presets_layout = QtWidgets.QVBoxLayout(presets_widget)
        presets_layout.setContentsMargins(0, 0, 0, 0)
        presets_layout.setSpacing(0)

        presets_layout.addWidget(scroll_widget, 1)
        presets_layout.addWidget(footer_widget, 0)

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.setLayout(layout)

        layout.addWidget(project_list_widget, 0)
        layout.addWidget(presets_widget, 1)

        btn.clicked.connect(self.___finish)

    def ___finish(self):
        output = {}
        for item in self.input_fields:
            output.update(item.config_value())

        for key in reversed(self.keys):
            _output = {key: output}
            output = _output

        print(json.dumps(output, indent=4))

    def add_children_gui(self, child_configuration, values):
        item_type = child_configuration["type"]
        klass = TypeToKlass.types.get(item_type)

        item = klass(
            child_configuration, values, self.keys, self
        )
        self.input_fields.append(item)
        self.content_layout.addWidget(item)
