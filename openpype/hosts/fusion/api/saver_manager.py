# TODO: Allow user to undo changes in the comp
# TODO: Add "load into comp" shortcut?
# TODO: Use os.scandir with newer Python versions (Python 3.6+ and Fusion 18+)

import os
import re
import sys
import traceback
import subprocess

from Qt import QtWidgets, QtCore, QtGui
import qtawesome

from openpype.style import load_stylesheet

from openpype import resources
from openpype.hosts.fusion.api import get_current_comp
from openpype.tools.utils.models import TreeModel, Item
from openpype.tools.utils import lib
from openpype.tools.utils.delegates import PrettyTimeDelegate


# TODO: Remove this debug workaround
# Debug crashes
def excepthook(type_, value, tb):
    print("".join(traceback.format_exception(type_, value, tb)))


sys.excepthook = excepthook

VERSION_PATTERN = "v([0-9]+)"
NO_VERSION = -1
ITEM_ROLE = TreeModel.ItemRole


def open_in_explorer(path):
    # todo(roy): Make this cross OS compatible (currently windows only)

    path = os.path.abspath(path)
    if os.path.isfile(path):
        # Select file in explorer
        cmd = 'explorer /select, "{0}"'.format(path)

    elif os.path.isdir(path):
        # Open folder in explorer
        cmd = r'explorer "{}"'.format(path)

    else:
        print("Path does not exist: %s" % path)
        return

    subprocess.Popen(cmd)


def set_clipboard(content):
    app = QtWidgets.QApplication.instance()
    assert app, "Must have running QApplication instance"

    # Set to Clipboard
    clipboard = QtWidgets.QApplication.clipboard()
    clipboard.setText(content)


class IconFactory(object):
    icons = {}

    @classmethod
    def icon(cls, icon_name, color=None):
        key = (icon_name, color)
        if key not in cls.icons:
            cls.icons[key] = qtawesome.icon(icon_name, color=color)
        return cls.icons[key]


class SearchReplaceDialog(QtWidgets.QDialog):
    """Search replace dialog"""

    replaced = QtCore.Signal(str, str)

    def __init__(self, *args, **kwargs):
        super(SearchReplaceDialog, self).__init__(*args, **kwargs)

        self.setWindowTitle("Search / Replace..")

        src_label = QtWidgets.QLabel("Find what:")
        src = QtWidgets.QLineEdit()
        src.setPlaceholderText("Before..")
        dest_label = QtWidgets.QLabel("Replace with:")
        dest = QtWidgets.QLineEdit()
        dest.setPlaceholderText("After..")

        form = QtWidgets.QFormLayout()
        form.addRow(src_label, src)
        form.addRow(dest_label, dest)

        apply = QtWidgets.QPushButton("Replace")

        self._dest = dest
        self._src = src

        layout = QtWidgets.QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(apply)

        apply.clicked.connect(self.on_apply)

    def on_apply(self):
        src = self._src.text()
        dest = self._dest.text()

        if not src:
            return

        self.replaced.emit(src, dest)


class PercentDelegate(QtWidgets.QStyledItemDelegate):
    """A delegate that display version integer formatted as version string."""

    def displayText(self, value, locale):
        return "{:.1f}%".format(value * 100.0)


class VersionDelegate(QtWidgets.QStyledItemDelegate):
    """A delegate that display version integer formatted as version string."""

    def displayText(self, value, locale):
        if value == NO_VERSION:
            return "No version"
        return lib.format_version(value)


def path_is_movie_format(path):
    """Mimics Fusion bmd.scriptlib's `pathIsMovieFormat`"""
    base, ext = os.path.splitext(path)
    return ext in {
        ".3gp", ".aac", ".aif", ".aiff", ".avi", ".dvs", ".fb", ".flv",
        ".m2ts", ".m4a", ".m4b", ".m4p", ".mkv", ".mov", ".mp3", ".mp4",
        ".mts", ".mxf", ".omf", ".omfi", ".qt", ".stm", ".tar", ".vdr",
        ".vpv", ".wav", ".webm"
    }


def get_saver_files(saver):
    """Mimics Fusion bmd.scriptlib's `SV_GetFrames`"""

    attrs = saver.GetAttrs()
    if saver.ID != "Saver":
        return []

    path = saver.Clip[0]
    if path_is_movie_format(path):
        return [path]

    # Get comp render range
    comp = saver.Composition
    comp_attrs = comp.GetAttrs()
    global_start = comp_attrs["COMPN_GlobalStart"]
    render_start = comp_attrs["COMPN_RenderStart"]
    render_end = comp_attrs["COMPN_RenderEnd"]
    length = render_end - render_start
    if saver.SetSequenceStart[comp.TIME_UNDEFINED] == 0:
        start = render_start
    else:
        sequence_start = saver.SequenceStartFrame[comp.TIME_UNDEFINED]
        start = sequence_start + render_start - global_start

    head, ext = os.path.splitext(path)
    # Get any trailing numbers to parse the intended padding
    match = re.match(".*?([0-9]+)$", head)
    padding = 0
    if match:
        trailing_number = match.group(1)
        padding = len(trailing_number)
        head = head[:-padding]

    files = []
    for frame in range(int(start), int(start + length + 1)):
        filepath = f"{head}{frame:0{padding}}{ext}"
        files.append(filepath)

    return files


class Model(TreeModel):
    Columns = ["name", "path", "version", "rendered", "date_modified"]
    Headers = ["Name", "Filepath", "Version", "Rendered", "Date Modified"]
    Column_indexes = {key: index for index, key in enumerate(Columns)}

    def refresh(self):

        self.clear()
        comp = get_current_comp()

        self.beginResetModel()

        for saver in comp.GetToolList(False, "Saver").values():
            item = self.get_item(saver, comp=comp)
            self.add_child(item)

        self.endResetModel()

    def get_item(self, saver, comp=None):

        if comp is None:
            comp = saver.Composition

        path = saver.Clip[comp.TIME_UNDEFINED]

        attrs = saver.GetAttrs()
        is_passthrough = attrs["TOOLB_PassThrough"]

        # Versions found in path
        versions = re.findall(VERSION_PATTERN, path)
        versions = set(versions)

        if len(versions) == 0:
            print(f"No versions found in existing filepath: {path}")
        elif len(versions) > 1:
            print(
                f"Multiple versions {list(versions)} found in existing "
                f"filepath: {path}")

        versions = [int(v) for v in versions]
        version = next(iter(versions), NO_VERSION)

        expected_files = get_saver_files(saver)
        existing_files = [path for path in expected_files if
                          os.path.exists(path)]
        percentage_rendered = len(existing_files) / float(len(expected_files))
        date_modified = None
        if existing_files:
            # Last date modified of the files
            date_modified = max(
                os.path.getmtime(path) for path in existing_files)

        color = "#79a8d0"  # default Fusion blue tile color
        tile_color = saver.TileColor
        if tile_color:
            color = QtGui.QColor.fromRgbF(tile_color["R"],
                                          tile_color["G"],
                                          tile_color["B"]).name()

        return Item({
            "name": saver.Name,
            "path": path,
            "version": version,
            "passthrough": is_passthrough,
            "tool": saver,
            "expected_files": get_saver_files,
            "existing_files": existing_files,
            "rendered": percentage_rendered,
            "date_modified": date_modified,
            "color": color
        })

    def data(self, index, role):
        if not index.isValid():
            return

        item = index.internalPointer()
        if role == QtCore.Qt.DecorationRole:
            # Add icon to name column
            if index.column() == 0:
                color = item["color"]
                icon = IconFactory.icon("fa.circle", color=color)
                return icon

        if role == QtCore.Qt.ForegroundRole:
            # Dim the font color when saver is set to passthrough
            if item["passthrough"]:
                return QtGui.QColor("#777777")

        return super(Model, self).data(index, role)

    def headerData(self, section, orientation, role=QtCore.Qt.DisplayRole):
        if orientation == QtCore.Qt.Horizontal and role == \
                QtCore.Qt.DisplayRole:
            if section < len(self.Headers):
                return self.Headers[section]
        return super().headerData(section, orientation, role)

    def set_version(self, index, version):
        item = index.internalPointer()
        item["version"] = version

        # Find the new path
        saver = item["tool"]
        path = item["path"]
        new_path = re.sub(VERSION_PATTERN, "v{0:03d}".format(version), path)

        if new_path == path:
            # No change
            return False

        saver.Clip = new_path
        self.update_row(index)
        return True

    def update_row(self, index):
        # todo: allow optimally updating multiple rows
        if not index.isValid():
            return

        item = index.internalPointer()
        saver = item["tool"]
        item.update(self.get_item(saver))

        # Emit edited data
        left = index.sibling(index.row(), 0)
        right = index.sibling(index.row(), len(self.Columns) - 1, )
        self.dataChanged.emit(left, right, [QtCore.Qt.DisplayRole])

    def setData(self, index, value, role):

        if not index.isValid():
            return

        if role == QtCore.Qt.EditRole:
            if index.column() == self.Column_indexes["version"]:
                return self.set_version(index, value)

        return super(Model, self).setData(value, role)

    def flags(self, index):
        flags = QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable

        # Make the version column editable
        if index.column() == self.Column_indexes["version"]:
            flags |= QtCore.Qt.ItemIsEditable

        return flags


class View(QtWidgets.QTreeView):
    def __init__(self, *args, **kwargs):
        super(View, self).__init__(*args, **kwargs)

        # Force entries to always be resized automatically with some padding
        # between the columns
        header = self.header()
        header.setSectionResizeMode(
            QtWidgets.QHeaderView.ResizeToContents
        )
        header.setStretchLastSection(True)
        style = "QTreeView::item {  border: 0px;  padding: 0 3px; }"
        self.setStyleSheet(style)

        self.setSelectionMode(self.ExtendedSelection)
        self.setIndentation(0)

        self.doubleClicked.connect(self.on_double_clicked)

    def keyPressEvent(self, event):

        if event.type() == QtCore.QEvent.KeyPress:
            key = event.key()

            # Select in Fusion
            if key in {QtCore.Qt.Key_Enter, QtCore.Qt.Key_Return}:
                self._select_selected_tools()
                event.accept()
                return

            # Increment / Decrement
            if key in {QtCore.Qt.Key_Plus, QtCore.Qt.Key_Minus}:
                change = {
                    QtCore.Qt.Key_Plus: 1,
                    QtCore.Qt.Key_Minus: -1
                }[key]
                self._increment_selected(change)
                event.accept()
                return

            # Copy paths to clipboard
            if event.matches(QtGui.QKeySequence.Copy):
                self._selected_paths_to_clipboard()
                event.accept()
                return

        super(View, self).keyPressEvent(event)

    def _selected_paths_to_clipboard(self):
        selected_rows = self.selectionModel().selectedRows()
        if not selected_rows:
            return

        paths = []
        for index in selected_rows:
            item = index.data(ITEM_ROLE)
            path = item["path"]
            paths.append(path)
        content = "\n".join(paths)
        set_clipboard(content)

    def _increment_selected(self, relative_change):
        selected_rows = self.selectionModel().selectedRows()
        if not selected_rows:
            return

        proxy = self.model()
        model = proxy.sourceModel()
        source_indexes = [proxy.mapToSource(index) for index in selected_rows]
        for source_index in source_indexes:
            item = source_index.data(ITEM_ROLE)
            version = item["version"]
            if version is NO_VERSION:
                continue
            version += relative_change

            model.set_version(source_index, version)

    def _select_selected_tools(self):
        selected_rows = self.selectionModel().selectedRows()
        if selected_rows:
            tool = selected_rows[0].data(ITEM_ROLE)["tool"]
            flow = tool.Composition.CurrentFrame.FlowView
            flow.Select()  # clear selection

            for index in selected_rows:
                saver = index.data(ITEM_ROLE)["tool"]
                flow.Select(saver, True)

    def on_double_clicked(self, index):
        if not index.isValid():
            return

        # item = index.data(ITEM_ROLE)
        # saver = item["tool"]
        # flow = saver.Composition.CurrentFrame.FlowView
        # flow.Select()  # clear selection
        # flow.Select(saver, True)
        self._select_selected_tools()


class FusionSaverManager(QtWidgets.QWidget):
    """Helper utility to manage Fusion Savers."""

    def __init__(self, parent=None):
        super(FusionSaverManager, self).__init__(parent)

        self.setWindowFlags(
            QtCore.Qt.Window
            | QtCore.Qt.CustomizeWindowHint
            | QtCore.Qt.WindowTitleHint
            | QtCore.Qt.WindowCloseButtonHint
            | QtCore.Qt.WindowStaysOnTopHint
        )

        self.setWindowTitle("OpenPype Fusion Saver Manager")
        self.setWindowIcon(QtGui.QIcon(resources.get_openpype_icon_filepath()))

        layout = QtWidgets.QVBoxLayout(self)

        toolbar = QtWidgets.QHBoxLayout()

        search_icon = IconFactory.icon("fa.search", color="#DDDDDD")
        search_replace_button = QtWidgets.QPushButton(search_icon, "Replace..")
        match_comp_icon = IconFactory.icon("fa.dot-circle-o", color="#DDDDDD")
        match_comp_version = QtWidgets.QPushButton(match_comp_icon,
                                                   "Match comp version")
        match_comp_version.setEnabled(False)
        show_in_explorer_icon = IconFactory.icon("fa.external-link",
                                                 color="#DDDDDD")
        show_in_explorer_button = QtWidgets.QPushButton(show_in_explorer_icon,
                                                        "Show in explorer")
        show_in_explorer_button.setEnabled(False)
        set_default_path_icon = IconFactory.icon("fa.external-link",
                                                 color="#DDDDDD")
        set_default_path_button = QtWidgets.QPushButton(set_default_path_icon,
                                                        "Set default path")
        set_default_path_button.setEnabled(False)
        refresh_icon = IconFactory.icon("fa.refresh", color="#7FB146")
        refresh = QtWidgets.QPushButton(refresh_icon, "Refresh")

        toolbar.addWidget(search_replace_button)
        toolbar.addWidget(match_comp_version)
        toolbar.addWidget(show_in_explorer_button)
        toolbar.addWidget(set_default_path_button)
        toolbar.addStretch()
        toolbar.addWidget(refresh)

        model = Model()
        proxy = QtCore.QSortFilterProxyModel()
        proxy.setDynamicSortFilter(True)
        proxy.setSourceModel(model)
        view = View()
        view.setSortingEnabled(True)
        view.sortByColumn(1, QtCore.Qt.AscendingOrder)
        view.setModel(proxy)

        version_delegate = VersionDelegate()
        view.setItemDelegateForColumn(2, version_delegate)

        percent_delegate = PercentDelegate()
        view.setItemDelegateForColumn(3, percent_delegate)

        date_delegate = PrettyTimeDelegate()
        view.setItemDelegateForColumn(4, date_delegate)

        self._delegates = [
            version_delegate,
            percent_delegate,
            date_delegate
        ]

        self.search_dialog = None

        layout.addLayout(toolbar)
        layout.addWidget(view)

        self.setStyleSheet(load_stylesheet())

        refresh.clicked.connect(model.refresh)

        self.search_replace_button = search_replace_button
        self.match_comp_version = match_comp_version
        self.show_in_explorer_button = show_in_explorer_button
        self.set_default_path_button = set_default_path_button
        self.refresh = refresh
        self.model = model
        self.proxy = proxy
        self.view = view

        self.resize(1600, 200)
        model.refresh()

        match_comp_version.clicked.connect(self.on_match_comp_version)
        search_replace_button.clicked.connect(self.on_show_search_replace)
        show_in_explorer_button.clicked.connect(self.on_show_in_explorer)
        set_default_path_button.clicked.connect(self.on_set_default_path)
        view.selectionModel().selectionChanged.connect(
            self.on_selection_changed)

    def on_show_search_replace(self):
        if not self.search_dialog:
            self.search_dialog = SearchReplaceDialog(parent=self)
            self.search_dialog.replaced.connect(self.on_search_replace)

        self.search_dialog.show()

    def on_show_in_explorer(self):

        rows = self.view.selectionModel().selectedRows()
        if not rows:
            return

        paths = []
        for row in rows:
            item = row.data(ITEM_ROLE)
            existing_files = item["existing_files"]
            if not existing_files:
                print(f"No files exist for: {item['path']}")
                continue
            first_file = existing_files[0]
            open_in_explorer(first_file)

    def on_search_replace(self, src, dst):

        rows = self.view.selectionModel().selectedRows()
        if not rows:
            return

        source_indexes = [self.proxy.mapToSource(index) for index in rows]
        for source_index in source_indexes:
            item = source_index.data(ITEM_ROLE)
            path = item["path"]
            new_path = path.replace(src, dst)
            saver = item["tool"]
            if path == new_path:
                continue

            saver.Clip = new_path
            print(f"{saver.Name}:")
            print(f"Before: {path}")
            print(f"After:  {new_path}")
            self.model.update_row(source_index)

    def on_set_default_path(self):
        # TODO: This is a rudimentary prototype and needs improvements!

        rows = self.view.selectionModel().selectedRows()
        if not rows:
            return

        # Get comp from first saver
        first_index = rows[0]
        saver = first_index.data(ITEM_ROLE)["tool"]
        comp = saver.Composition
        comp_path = comp.GetAttrs()["COMPS_FileName"]
        version = self.__get_version(os.path.basename(comp_path)) or 1

        # TODO: Implement better way to define default path
        task_root = os.path.dirname(os.path.dirname(comp_path))
        version_formatted = lib.format_version(version)
        renders_root = os.path.join(task_root, "renders", version_formatted)

        source_indexes = [self.proxy.mapToSource(index) for index in rows]
        for source_index in source_indexes:

            item = source_index.data(ITEM_ROLE)
            saver = item["tool"]
            path = item["path"]
            base, ext = os.path.splitext(path)
            frame = "" if path_is_movie_format(path) else ".0000"
            fname = f"{saver.Name}_{version_formatted}{frame}{ext}"
            default_saver_path = os.path.join(renders_root, fname)
            if path == default_saver_path:
                continue

            saver.Clip = default_saver_path
            print(f"{saver.Name}:")
            print(f"Before: {path}")
            print(f"After:  {default_saver_path}")
            self.model.update_row(source_index)

    def on_match_comp_version(self):

        rows = self.view.selectionModel().selectedRows()
        if not rows:
            return

        # Get composition's version from comp of first selected saver
        first_index = rows[0]
        saver = first_index.data(ITEM_ROLE)["tool"]
        comp = saver.Composition
        comp_path = os.path.basename(comp.GetAttrs()["COMPS_FileName"])
        comp_version = self.__get_version(comp_path)

        print(f"Detected comp version: {lib.format_version(comp_version)}")
        source_indexes = [self.proxy.mapToSource(index) for index in rows]
        for source_index in source_indexes:
            self.model.set_version(source_index, comp_version)

    def __get_version(self, path):

        versions = set(int(v) for v in re.findall("v([0-9]+)", path))
        if not versions:
            print(f"No version found in filename: {path}")
            return
        elif len(versions) > 1:
            print(
                f"More than a single version string found in filename: "
                f"{path} ({versions})")
            return max(versions)
        else:
            return next(iter(versions))

    def on_selection_changed(self):

        selected_rows = self.view.selectionModel().selectedRows()
        has_selection = any(selected_rows)

        self.match_comp_version.setEnabled(has_selection)
        self.show_in_explorer_button.setEnabled(has_selection)
        self.set_default_path_button.setEnabled(has_selection)


def launch():
    app = QtWidgets.QApplication(sys.argv)

    window = FusionSaverManager()

    stylesheet = load_stylesheet()
    window.setStyleSheet(stylesheet)

    window.show()

    result = app.exec_()
    print("Shutting down..")
    sys.exit(result)
