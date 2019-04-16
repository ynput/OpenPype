import os
import clique
from . import QtWidgets, QtCore
from . import ComponentItem, TreeComponents, DropDataWidget


class DropDataFrame(QtWidgets.QFrame):
    # signal_dropped = QtCore.Signal(object)

    def __init__(self, parent):
        super().__init__()

        self.items = []

        self.setAcceptDrops(True)
        layout = QtWidgets.QVBoxLayout(self)

        self.tree_widget = TreeComponents(self)
        layout.addWidget(self.tree_widget)

        self.drop_widget = DropDataWidget(self)
        layout.addWidget(self.drop_widget)

        self._refresh_view()

    def dragEnterEvent(self, event):
        event.setDropAction(QtCore.Qt.CopyAction)
        event.accept()

    def dragLeaveEvent(self, event):
        event.accept()

    def dropEvent(self, event):
        paths = self._processMimeData(event.mimeData())
        if paths:
            self._add_components(paths)
        event.accept()

    def _processMimeData(self, mimeData):
        paths = []

        if not mimeData.hasUrls():
            print('Dropped invalid file/folder')
            return paths

        for path in mimeData.urls():
            local_path = path.toLocalFile()
            if os.path.isfile(local_path) or os.path.isdir(local_path):
                paths.append(local_path)
            else:
                print('Invalid input: "{}"'.format(local_path))

        return paths

    def _add_components(self, paths):
        components = self._process_paths(paths)
        if not components:
            return
        for component in components:
            self._add_item(component)

    def _add_item(self, data):
        # Assign to self so garbage collector wont remove the component
        # during initialization
        self.new_component = ComponentItem(self.tree_widget, data)
        self.new_component._widget.signal_remove.connect(self._remove_item)
        self.tree_widget.addTopLevelItem(self.new_component)
        self.items.append(self.new_component)
        self.new_component = None

        self._refresh_view()

    def _remove_item(self, item):
        root = self.tree_widget.invisibleRootItem()
        (item.parent() or root).removeChild(item)
        self.items.remove(item)
        self._refresh_view()

    def _refresh_view(self):
        _bool = len(self.items) == 0

        self.tree_widget.setVisible(not _bool)
        self.drop_widget.setVisible(_bool)

    def _process_paths(self, in_paths):
        paths = self._get_all_paths(in_paths)
        collections, remainders = clique.assemble(paths)
        for collection in collections:
            self._process_collection(collection)
        for remainder in remainders:
            self._process_remainder(remainder)

    def _get_all_paths(self, paths):
        output_paths = []
        for path in paths:
            path = os.path.normpath(path)
            if os.path.isfile(path):
                output_paths.append(path)
            elif os.path.isdir(path):
                s_paths = []
                for s_item in os.listdir(path):
                    s_path = os.path.sep.join([path, s_item])
                    s_paths.append(s_path)
                output_paths.extend(self._get_all_paths(s_paths))
            else:
                print('Invalid path: "{}"'.format(path))
        return output_paths

    def _process_collection(self, collection):
        file_base = os.path.basename(collection.head)
        folder_path = os.path.dirname(collection.head)
        if file_base[-1] in ['.']:
            file_base = file_base[:-1]
        file_ext = collection.tail
        repr_name = file_ext.replace('.', '')
        range = self._get_ranges(collection.indexes)
        thumb = False
        if file_ext in ['.jpeg']:
            thumb = True

        prev = False
        if file_ext in ['.jpeg']:
            prev = True

        files = []
        for file in os.listdir(folder_path):
            if file.startswith(file_base) and file.endswith(file_ext):
                files.append(os.path.sep.join([folder_path, file]))
        info = {}

        data = {
            'files': files,
            'name': file_base,
            'ext': file_ext,
            'file_info': range,
            'representation': repr_name,
            'folder_path': folder_path,
            'icon': 'sequence',
            'thumb': thumb,
            'prev': prev,
            'is_sequence': True,
            'info': info
        }
        self._process_data(data)

    def _get_ranges(self, indexes):
        if len(indexes) == 1:
            return str(indexes[0])
        ranges = []
        first = None
        last = None
        for index in indexes:
            if first is None:
                first = index
                last = index
            elif (last+1) == index:
                last = index
            else:
                if first == last:
                    range = str(first)
                else:
                    range = '{}-{}'.format(first, last)
                ranges.append(range)
                first = index
                last = index
        if first == last:
            range = str(first)
        else:
            range = '{}-{}'.format(first, last)
        ranges.append(range)
        return ', '.join(ranges)

    def _process_remainder(self, remainder):
        filename = os.path.basename(remainder)
        folder_path = os.path.dirname(remainder)
        file_base, file_ext = os.path.splitext(filename)
        repr_name = file_ext.replace('.', '')
        file_info = None
        thumb = False
        if file_ext in ['.jpeg']:
            thumb = True

        prev = False
        if file_ext in ['.jpeg']:
            prev = True

        files = []
        files.append(remainder)

        info = {}

        data = {
            'files': files,
            'name': file_base,
            'ext': file_ext,
            'file_info': file_info,
            'representation': repr_name,
            'folder_path': folder_path,
            'icon': 'sequence',
            'thumb': thumb,
            'prev': prev,
            'is_sequence': False,
            'info': info
        }

        self._process_data(data)

    def _process_data(self, data):
        found = False
        for item in self.items:
            if data['ext'] != item.in_data['ext']:
                continue
            if data['folder_path'] != item.in_data['folder_path']:
                continue

            new_is_seq = data['is_sequence']
            ex_is_seq = item.in_data['is_sequence']

            # If both are single files
            if not new_is_seq and not ex_is_seq:
                if data['name'] != item.in_data['name']:
                    continue
                found = True
                break
            # If new is sequence and ex is single file
            elif new_is_seq and not ex_is_seq:
                if data['name'] not in item.in_data['name']:
                    continue
                ex_file = item.in_data['files'][0]
                found = True
                # If file is one of inserted sequence
                if ex_file in data['files']:
                    self._remove_item(item)
                    self._add_item(data)
                    break
                # if file is missing in inserted sequence
                paths = data['files']
                paths.append(ex_file)
                collections, remainders = clique.assemble(paths)
                self._process_collection(collections[0])
                break
            # If new is single file existing is sequence
            elif not new_is_seq and ex_is_seq:
                if item.in_data['name'] not in data['name']:
                    continue
                new_file = data['files'][0]
                found = True
                if new_file in item.in_data['files']:
                    break
                paths = item.in_data['files']
                paths.append(new_file)
                collections, remainders = clique.assemble(paths)
                self._remove_item(item)
                self._process_collection(collections[0])

                break
            # If both are sequence
            else:
                if data['name'] != item.in_data['name']:
                    continue
                found = True
                ex_files = item.in_data['files']
                for file in data['files']:
                    if file not in ex_files:
                        ex_files.append(file)
                paths = list(set(ex_files))
                collections, remainders = clique.assemble(paths)
                self._remove_item(item)
                self._process_collection(collections[0])
                break

        if found is False:
            self._add_item(data)
