import platform
from Qt import QtWidgets
from .widgets import (
    Separator,
    ExpandingWidget
)
from openpype.tools.settings import CHILD_OFFSET
from openpype.tools.utils import PlaceholderLineEdit


class AppVariantWidget(QtWidgets.QWidget):
    exec_placeholder = "< Specific path for this machine >"

    def __init__(
        self, group_label, variant_name, variant_label, variant_entity, parent
    ):
        super(AppVariantWidget, self).__init__(parent)

        self.executable_input_widget = None

        if not variant_label:
            variant_label = variant_name

        label = " ".join([group_label, variant_label])

        expading_widget = ExpandingWidget(label, self)
        content_widget = QtWidgets.QWidget(expading_widget)
        content_layout = QtWidgets.QVBoxLayout(content_widget)
        content_layout.setContentsMargins(CHILD_OFFSET, 5, 0, 0)

        expading_widget.set_content_widget(content_widget)

        # Add expanding widget to main layout
        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(expading_widget)

        # TODO For celaction - not sure what is "Celaction publish" for
        if not variant_entity["executables"].multiplatform:
            warn_label = QtWidgets.QLabel(
                "Application without multiplatform paths"
            )
            content_layout.addWidget(warn_label)
            return

        executable_input_widget = PlaceholderLineEdit(content_widget)
        executable_input_widget.setPlaceholderText(self.exec_placeholder)
        content_layout.addWidget(executable_input_widget)

        self.executable_input_widget = executable_input_widget

        studio_executables = (
            variant_entity["executables"][platform.system().lower()]
        )
        if len(studio_executables) < 1:
            return

        content_layout.addWidget(Separator(parent=self))
        content_layout.addWidget(
            QtWidgets.QLabel("Studio paths:", self)
        )

        for item in studio_executables:
            path_widget = QtWidgets.QLineEdit(content_widget)
            path_widget.setObjectName("LikeDisabledInput")
            path_widget.setText(item.value)
            path_widget.setReadOnly(True)
            content_layout.addWidget(path_widget)

    def update_local_settings(self, value):
        if not self.executable_input_widget:
            return

        if not value:
            value = {}
        elif not isinstance(value, dict):
            print("Got invalid value type {}. Expected {}".format(
                type(value), dict
            ))
            value = {}

        executable_path = value.get("executable")
        if not executable_path:
            executable_path = ""
        elif isinstance(executable_path, list):
            print("Got list in executable path so using first item as value")
            executable_path = executable_path[0]

        if not isinstance(executable_path, str):
            executable_path = ""
            print((
                "Got invalid value type of app executable {}. Expected {}"
            ).format(type(value), str))

        self.executable_input_widget.setText(executable_path)

    def settings_value(self):
        if not self.executable_input_widget:
            return None
        value = self.executable_input_widget.text()
        if not value:
            return None
        return {"executable": value}


class AppGroupWidget(QtWidgets.QWidget):
    def __init__(self, group_entity, group_label, parent, dynamic=False):
        super(AppGroupWidget, self).__init__(parent)

        variants_entity = group_entity["variants"]
        valid_variants = {}
        for key, entity in variants_entity.items():
            if "enabled" not in entity or entity["enabled"].value:
                valid_variants[key] = entity

        expading_widget = ExpandingWidget(group_label, self)
        content_widget = QtWidgets.QWidget(expading_widget)
        content_layout = QtWidgets.QVBoxLayout(content_widget)
        content_layout.setContentsMargins(CHILD_OFFSET, 5, 0, 0)

        widgets_by_variant_name = {}
        for variant_name, variant_entity in valid_variants.items():
            if "executables" not in variant_entity:
                continue

            variant_label = variant_entity.label
            if dynamic and hasattr(variants_entity, "get_key_label"):
                variant_label = variants_entity.get_key_label(variant_name)

            variant_widget = AppVariantWidget(
                group_label,
                variant_name,
                variant_label,
                variant_entity,
                content_widget
            )
            widgets_by_variant_name[variant_name] = variant_widget
            content_layout.addWidget(variant_widget)

        expading_widget.set_content_widget(content_widget)

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(expading_widget)

        self.widgets_by_variant_name = widgets_by_variant_name

    def update_local_settings(self, value):
        if not value:
            value = {}

        for variant_name, widget in self.widgets_by_variant_name.items():
            widget.update_local_settings(value.get(variant_name))

    def settings_value(self):
        output = {}
        for variant_name, widget in self.widgets_by_variant_name.items():
            value = widget.settings_value()
            if value:
                output[variant_name] = value

        if not output:
            return None
        return output


class LocalApplicationsWidgets(QtWidgets.QWidget):
    def __init__(self, system_settings_entity, parent):
        super(LocalApplicationsWidgets, self).__init__(parent)

        self.widgets_by_group_name = {}
        self.system_settings_entity = system_settings_entity

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.content_layout = layout

    def _filter_group_entity(self, entity):
        if not entity["enabled"].value:
            return False

        # Check if has enabled any variant
        for variant_entity in entity["variants"].values():
            if (
                "enabled" not in variant_entity
                or variant_entity["enabled"].value
            ):
                return True

        return False

    def _reset_app_widgets(self):
        while self.content_layout.count() > 0:
            item = self.content_layout.itemAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setVisible(False)
            self.content_layout.removeItem(item)
        self.widgets_by_group_name.clear()

        app_items = {}
        additional_apps = set()
        additional_apps_entity = None
        for key, entity in self.system_settings_entity["applications"].items():
            if key != "additional_apps":
                app_items[key] = entity
                continue

            additional_apps_entity = entity
            for _key, _entity in entity.items():
                app_items[_key] = _entity
                additional_apps.add(_key)

        for key, entity in app_items.items():
            if not self._filter_group_entity(entity):
                continue

            dynamic = key in additional_apps
            group_label = None
            if dynamic and hasattr(additional_apps_entity, "get_key_label"):
                group_label = additional_apps_entity.get_key_label(key)

            if not group_label:
                group_label = entity.label
                if not group_label:
                    group_label = key

            # Create App group specific widget and store it by the key
            group_widget = AppGroupWidget(entity, group_label, self, dynamic)
            if group_widget.widgets_by_variant_name:
                self.widgets_by_group_name[key] = group_widget
                self.content_layout.addWidget(group_widget)
            else:
                group_widget.setVisible(False)
                group_widget.deleteLater()

    def update_local_settings(self, value):
        if not value:
            value = {}

        self._reset_app_widgets()

        for group_name, widget in self.widgets_by_group_name.items():
            widget.update_local_settings(value.get(group_name))

    def settings_value(self):
        output = {}
        for group_name, widget in self.widgets_by_group_name.items():
            value = widget.settings_value()
            if value:
                output[group_name] = value
        if not output:
            return None
        return output
