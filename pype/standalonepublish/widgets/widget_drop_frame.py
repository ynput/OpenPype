import os
import clique
import subprocess
from pypeapp import config
from . import QtWidgets, QtCore
from . import DropEmpty, ComponentsList, ComponentItem


class DropDataFrame(QtWidgets.QFrame):
    def __init__(self, parent):
        super().__init__()
        self.parent_widget = parent
        self.items = []
        self.presets = config.get_presets()['standalone_publish']

        self.setAcceptDrops(True)
        layout = QtWidgets.QVBoxLayout(self)
        self.components_list = ComponentsList(self)
        layout.addWidget(self.components_list)

        self.drop_widget = DropEmpty(self)

        sizePolicy = QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.drop_widget.sizePolicy().hasHeightForWidth())
        self.drop_widget.setSizePolicy(sizePolicy)

        layout.addWidget(self.drop_widget)

        self._refresh_view()

    def dragEnterEvent(self, event):
        event.setDropAction(QtCore.Qt.CopyAction)
        event.accept()

    def dragLeaveEvent(self, event):
        event.accept()

    def dropEvent(self, event):
        self.process_ent_mime(event)
        event.accept()

    def process_ent_mime(self, ent):
        paths = []
        if ent.mimeData().hasUrls():
            paths = self._processMimeData(ent.mimeData())
        else:
            # If path is in clipboard as string
            try:
                path = ent.text()
                if os.path.exists(path):
                    paths.append(path)
                else:
                    print('Dropped invalid file/folder')
            except Exception:
                pass
        if paths:
            self._process_paths(paths)

    def _processMimeData(self, mimeData):
        paths = []

        for path in mimeData.urls():
            local_path = path.toLocalFile()
            if os.path.isfile(local_path) or os.path.isdir(local_path):
                paths.append(local_path)
            else:
                print('Invalid input: "{}"'.format(local_path))
        return paths

    def _add_item(self, data, actions=[]):
        # Assign to self so garbage collector wont remove the component
        # during initialization
        new_component = ComponentItem(self.components_list, self)
        new_component.set_context(data)
        self.components_list.add_widget(new_component)

        new_component.signal_remove.connect(self._remove_item)
        new_component.signal_preview.connect(self._set_preview)
        new_component.signal_thumbnail.connect(
            self._set_thumbnail
        )
        for action in actions:
            new_component.add_action(action)

        self.items.append(new_component)

        self._refresh_view()

    def _set_thumbnail(self, in_item):
        checked_item = None
        for item in self.items:
            if item.is_thumbnail():
                checked_item = item
                break
        if checked_item is None or checked_item == in_item:
            in_item.change_thumbnail()
        else:
            checked_item.change_thumbnail(False)
            in_item.change_thumbnail()

    def _set_preview(self, in_item):
        checked_item = None
        for item in self.items:
            if item.is_preview():
                checked_item = item
                break
        if checked_item is None or checked_item == in_item:
            in_item.change_preview()
        else:
            checked_item.change_preview(False)
            in_item.change_preview()

    def _remove_item(self, item):
        index = self.components_list.widget_index(item)
        self.components_list.remove_widget(index)
        if item in self.items:
            self.items.remove(item)
        self._refresh_view()

    def _refresh_view(self):
        _bool = len(self.items) == 0
        self.components_list.setVisible(not _bool)
        self.drop_widget.setVisible(_bool)

        self.parent_widget.set_valid_components(not _bool)

    def _process_paths(self, in_paths):
        self.parent_widget.working_start()
        paths = self._get_all_paths(in_paths)
        collections, remainders = clique.assemble(paths)
        for collection in collections:
            self._process_collection(collection)
        for remainder in remainders:
            self._process_remainder(remainder)
        self.parent_widget.working_stop()

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
        if file_base[-1] in ['.', '_']:
            file_base = file_base[:-1]
        file_ext = collection.tail
        repr_name = file_ext.replace('.', '')
        range = collection.format('{ranges}')

        actions = []

        data = {
            'files': [file for file in collection],
            'name': file_base,
            'ext': file_ext,
            'file_info': range,
            'representation': repr_name,
            'folder_path': folder_path,
            'is_sequence': True,
            'actions': actions
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

        files = []
        files.append(remainder)

        actions = []

        data = {
            'files': files,
            'name': file_base,
            'ext': file_ext,
            'representation': repr_name,
            'folder_path': folder_path,
            'is_sequence': False,
            'actions': actions
        }
        data['file_info'] = self.get_file_info(data)

        self._process_data(data)

    def get_file_info(self, data):
        output = None
        if data['ext'] == '.mov':
            try:
                # ffProbe must be in PATH
                filepath = data['files'][0]
                args = ['ffprobe', '-show_streams', filepath]
                p = subprocess.Popen(
                    args,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    shell=True
                )
                datalines=[]
                for line in iter(p.stdout.readline, b''):
                    line = line.decode("utf-8").replace('\r\n', '')
                    datalines.append(line)

                find_value = 'codec_name'
                for line in datalines:
                    if line.startswith(find_value):
                        output = line.replace(find_value + '=', '')
                        break
            except Exception as e:
                pass
        return output

    def _process_data(self, data):
        ext = data['ext']
        icon = 'default'
        for ico, exts in self.presets['extensions'].items():
            if ext in exts:
                icon = ico
                break
        # Add 's' to icon_name if is sequence (image -> images)
        if data['is_sequence']:
            icon += 's'
        data['icon'] = icon
        data['thumb'] = (
            ext in self.presets['extensions']['thumbnailable'] and
            data['is_sequence'] is False
        )
        data['prev'] = ext in self.presets['extensions']['video_file']

        actions = []
        new_is_seq = data['is_sequence']

        found = False
        for item in self.items:
            if data['ext'] != item.in_data['ext']:
                continue
            if data['folder_path'] != item.in_data['folder_path']:
                continue

            ex_is_seq = item.in_data['is_sequence']

            # If both are single files
            if not new_is_seq and not ex_is_seq:
                if data['name'] == item.in_data['name']:
                    found = True
                    break
                paths = data['files']
                paths.extend(item.in_data['files'])
                c, r = clique.assemble(paths)
                if len(c) == 0:
                    continue
                a_name = 'merge'
                item.add_action(a_name)
                if a_name not in actions:
                    actions.append(a_name)

            # If new is sequence and ex is single file
            elif new_is_seq and not ex_is_seq:
                if data['name'] not in item.in_data['name']:
                    continue
                ex_file = item.in_data['files'][0]

                a_name = 'merge'
                item.add_action(a_name)
                if a_name not in actions:
                    actions.append(a_name)
                continue

            # If new is single file existing is sequence
            elif not new_is_seq and ex_is_seq:
                if item.in_data['name'] not in data['name']:
                    continue
                a_name = 'merge'
                item.add_action(a_name)
                if a_name not in actions:
                    actions.append(a_name)

            # If both are sequence
            else:
                if data['name'] != item.in_data['name']:
                    continue
                if data['files'] == item.in_data['files']:
                    found = True
                    break
                a_name = 'merge'
                item.add_action(a_name)
                if a_name not in actions:
                    actions.append(a_name)

        if new_is_seq:
            actions.append('split')

        if found is False:
            self._add_item(data, actions)

    def merge_items(self, in_item):
        self.parent_widget.working_start()
        items = []
        in_paths = in_item.in_data['files']
        paths = in_paths
        for item in self.items:
            if item.in_data['files'] == in_paths:
                items.append(item)
                continue
            copy_paths = paths.copy()
            copy_paths.extend(item.in_data['files'])
            collections, remainders = clique.assemble(copy_paths)
            if len(collections) == 1 and len(remainders) == 0:
                paths.extend(item.in_data['files'])
                items.append(item)
        for item in items:
            self._remove_item(item)
        self._process_paths(paths)
        self.parent_widget.working_stop()

    def split_items(self, item):
        self.parent_widget.working_start()
        paths = item.in_data['files']
        self._remove_item(item)
        for path in paths:
            self._process_remainder(path)
        self.parent_widget.working_stop()

    def collect_data(self):
        data = {'components' : []}
        for item in self.items:
            data['components'].append(item.collect_data())
        return data
