import datetime

from qtpy import QtWidgets

from openpype.tools.utils.lib import format_version


class VersionTextEdit(QtWidgets.QTextEdit):
    """QTextEdit that displays version specific information.

    This also overrides the context menu to add actions like copying
    source path to clipboard or copying the raw data of the version
    to clipboard.

    """
    def __init__(self, controller, parent):
        super(VersionTextEdit, self).__init__(parent=parent)

        self._version_item = None
        self._product_item = None

        self._controller = controller

        # Reset
        self.set_current_item()

    def set_current_item(self, product_item=None, version_item=None):
        """

        Args:
            product_item (Union[ProductItem, None]): Product item.
            version_item (Union[VersionItem, None]): Version item to display.
        """

        self._product_item = product_item
        self._version_item = version_item

        if version_item is None:
            # Reset state to empty
            self.setText("")
            return

        version_label = format_version(abs(version_item.version))
        if version_item.version < 0:
            version_label = "Hero version {}".format(version_label)

        # Define readable creation timestamp
        created = version_item.published_time
        created = datetime.datetime.strptime(created, "%Y%m%dT%H%M%SZ")
        created = datetime.datetime.strftime(created, "%b %d %Y %H:%M")

        comment = version_item.comment or "No comment"
        source = version_item.source or "No source"

        self.setHtml(
            (
                "<h2>{product_name}</h2>"
                "<h3>{version_label}</h3>"
                "<b>Comment</b><br>"
                "{comment}<br><br>"

                "<b>Created</b><br>"
                "{created}<br><br>"

                "<b>Source</b><br>"
                "{source}"
            ).format(
                product_name=product_item.product_name,
                version_label=version_label,
                comment=comment,
                created=created,
                source=source,
            )
        )

    def contextMenuEvent(self, event):
        """Context menu with additional actions"""
        menu = self.createStandardContextMenu()

        # Add additional actions when any text, so we can assume
        #   the version is set.
        source = None
        if self._version_item is not None:
            source = self._version_item.source

        if source:
            menu.addSeparator()
            action = QtWidgets.QAction(
                "Copy source path to clipboard", menu
            )
            action.triggered.connect(self._on_copy_source)
            menu.addAction(action)

        menu.exec_(event.globalPos())

    def _on_copy_source(self):
        """Copy formatted source path to clipboard."""

        source = self._version_item.source
        if not source:
            return

        filled_source = self._controller.fill_root_in_source(source)
        clipboard = QtWidgets.QApplication.clipboard()
        clipboard.setText(filled_source)


class InfoWidget(QtWidgets.QWidget):
    """A Widget that display information about a specific version"""
    def __init__(self, controller, parent):
        super(InfoWidget, self).__init__(parent=parent)

        label_widget = QtWidgets.QLabel("Version Info", self)
        info_text_widget = VersionTextEdit(controller, self)
        info_text_widget.setReadOnly(True)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(label_widget, 0)
        layout.addWidget(info_text_widget, 1)

        self._controller = controller

        self._info_text_widget = info_text_widget
        self._label_widget = label_widget

    def set_selected_version_info(self, project_name, items):
        if not items or not project_name:
            self._info_text_widget.set_current_item()
            return
        first_item = next(iter(items))
        product_item = self._controller.get_product_item(
            project_name,
            first_item["product_id"],
        )
        version_id = first_item["version_id"]
        version_item = None
        if product_item is not None:
            version_item = product_item.version_items.get(version_id)

        self._info_text_widget.set_current_item(product_item, version_item)
