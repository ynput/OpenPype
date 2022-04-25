import os
import re
import json
import clique
import subprocess
import openpype.lib
from Qt import QtWidgets, QtCore
from . import DropEmpty, ComponentsList, ComponentItem


class DropDataFrame(QtWidgets.QFrame):
    image_extensions = [
        ".ani", ".anim", ".apng", ".art", ".bmp", ".bpg", ".bsave", ".cal",
        ".cin", ".cpc", ".cpt", ".dds", ".dpx", ".ecw", ".exr", ".fits",
        ".flic", ".flif", ".fpx", ".gif", ".hdri", ".hevc", ".icer",
        ".icns", ".ico", ".cur", ".ics", ".ilbm", ".jbig", ".jbig2",
        ".jng", ".jpeg", ".jpeg-ls", ".jpeg", ".2000", ".jpg", ".xr",
        ".jpeg", ".xt", ".jpeg-hdr", ".kra", ".mng", ".miff", ".nrrd",
        ".ora", ".pam", ".pbm", ".pgm", ".ppm", ".pnm", ".pcx", ".pgf",
        ".pictor", ".png", ".psb", ".psp", ".qtvr", ".ras",
        ".rgbe", ".logluv", ".tiff", ".sgi", ".tga", ".tiff", ".tiff/ep",
        ".tiff/it", ".ufo", ".ufp", ".wbmp", ".webp", ".xbm", ".xcf",
        ".xpm", ".xwd"
    ]
    video_extensions = [
        ".3g2", ".3gp", ".amv", ".asf", ".avi", ".drc", ".f4a", ".f4b",
        ".f4p", ".f4v", ".flv", ".gif", ".gifv", ".m2v", ".m4p", ".m4v",
        ".mkv", ".mng", ".mov", ".mp2", ".mp4", ".mpe", ".mpeg", ".mpg",
        ".mpv", ".mxf", ".nsv", ".ogg", ".ogv", ".qt", ".rm", ".rmvb",
        ".roq", ".svi", ".vob", ".webm", ".wmv", ".yuv"
    ]
    extensions = {
        "nuke": [".nk"],
        "maya": [".ma", ".mb"],
        "houdini": [".hip"],
        "image_file": image_extensions,
        "video_file": video_extensions
    }

    sequence_types = [
        ".bgeo", ".vdb"
    ]

    def __init__(self, parent):
        super().__init__()
        self.parent_widget = parent

        self.setAcceptDrops(True)
        layout = QtWidgets.QVBoxLayout(self)
        self.components_list = ComponentsList(self)
        layout.addWidget(self.components_list)

        self.drop_widget = DropEmpty(self)

        sizePolicy = QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(
            self.drop_widget.sizePolicy().hasHeightForWidth()
        )
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
                path = os.path.normpath(ent.text())
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
        # Assign to self so garbage collector won't remove the component
        # during initialization
        new_component = ComponentItem(self.components_list, self)
        new_component.set_context(data)
        self.components_list.add_widget(new_component)

        new_component.signal_remove.connect(self._remove_item)
        new_component.signal_preview.connect(self._set_preview)
        new_component.signal_thumbnail.connect(
            self._set_thumbnail
        )
        new_component.signal_repre_change.connect(self.repre_name_changed)
        for action in actions:
            new_component.add_action(action)

        if len(self.components_list.widgets()) == 1:
            self.parent_widget.set_valid_repre_names(True)
        self._refresh_view()

    def _set_thumbnail(self, in_item):
        current_state = in_item.is_thumbnail()
        in_item.change_thumbnail(not current_state)

        checked_item = None
        for item in self.components_list.widgets():
            if item.is_thumbnail():
                checked_item = item
                break
        if checked_item is not None and checked_item != in_item:
            checked_item.change_thumbnail(False)

        in_item.change_thumbnail(current_state)

    def _set_preview(self, in_item):
        current_state = in_item.is_preview()
        in_item.change_preview(not current_state)

        checked_item = None
        for item in self.components_list.widgets():
            if item.is_preview():
                checked_item = item
                break
        if checked_item is not None and checked_item != in_item:
            checked_item.change_preview(False)

        in_item.change_preview(current_state)

    def _remove_item(self, in_item):
        valid_repre = in_item.has_valid_repre is True

        self.components_list.remove_widget(
            self.components_list.widget_index(in_item)
        )
        self._refresh_view()
        if valid_repre:
            return
        for item in self.components_list.widgets():
            if item.has_valid_repre:
                continue
            self.repre_name_changed(item, item.input_repre.text())

    def _refresh_view(self):
        _bool = len(self.components_list.widgets()) == 0
        self.components_list.setVisible(not _bool)
        self.drop_widget.setVisible(_bool)

        self.parent_widget.set_valid_components(not _bool)

    def _process_paths(self, in_paths):
        self.parent_widget.working_start()
        paths = self._get_all_paths(in_paths)
        collectionable_paths = []
        non_collectionable_paths = []
        for path in in_paths:
            ext = os.path.splitext(path)[1]
            if ext in self.image_extensions or ext in self.sequence_types:
                collectionable_paths.append(path)
            else:
                non_collectionable_paths.append(path)

        collections, remainders = clique.assemble(collectionable_paths)
        non_collectionable_paths.extend(remainders)
        for collection in collections:
            self._process_collection(collection)

        for remainder in non_collectionable_paths:
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
        file_ext = os.path.splitext(
            collection.format('{head}{padding}{tail}'))[1]
        repr_name = file_ext.replace('.', '')
        range = collection.format('{ranges}')

        # TODO: ranges must not be with missing frames!!!
        # - this is goal implementation:
        # startFrame, endFrame = range.split('-')
        rngs = range.split(',')
        startFrame = rngs[0].split('-')[0]
        endFrame = rngs[-1].split('-')[-1]

        actions = []

        data = {
            'files': [file for file in collection],
            'name': file_base,
            'ext': file_ext,
            'file_info': range,
            "frameStart": startFrame,
            "frameEnd": endFrame,
            'representation': repr_name,
            'folder_path': folder_path,
            'is_sequence': True,
            'actions': actions
        }

        self._process_data(data)

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

        self._process_data(data)

    def load_data_with_probe(self, filepath):
        ffprobe_path = openpype.lib.get_ffmpeg_tool_path("ffprobe")
        args = [
            "\"{}\"".format(ffprobe_path),
            '-v', 'quiet',
            '-print_format json',
            '-show_format',
            '-show_streams',
            '"{}"'.format(filepath)
        ]
        ffprobe_p = subprocess.Popen(
            ' '.join(args),
            stdout=subprocess.PIPE,
            shell=True
        )
        ffprobe_output = ffprobe_p.communicate()[0]
        if ffprobe_p.returncode != 0:
            raise RuntimeError(
                'Failed on ffprobe: check if ffprobe path is set in PATH env'
            )
        return json.loads(ffprobe_output)['streams'][0]

    def get_file_data(self, data):
        filepath = data['files'][0]
        ext = data['ext'].lower()
        output = {"fps": None}

        file_info = None
        if 'file_info' in data:
            file_info = data['file_info']

        if ext in self.image_extensions or ext in self.video_extensions:
            probe_data = self.load_data_with_probe(filepath)
            if 'fps' not in data:
                # default value
                fps = 25
                fps_string = probe_data.get('r_frame_rate')
                if fps_string:
                    fps = int(fps_string.split('/')[0])

                output['fps'] = fps

            if "frameStart" not in data or "frameEnd" not in data:
                startFrame = endFrame = 1
                endFrame_string = probe_data.get('nb_frames')

                if endFrame_string:
                    endFrame = int(endFrame_string)

                output["frameStart"] = startFrame
                output["frameEnd"] = endFrame

            if (ext == '.mov') and (not file_info):
                file_info = probe_data.get('codec_name')

        output['file_info'] = file_info

        return output

    def _process_data(self, data):
        ext = data['ext']
        # load file data info
        file_data = self.get_file_data(data)
        for key, value in file_data.items():
            data[key] = value

        icon = 'default'
        for ico, exts in self.extensions.items():
            if ext in exts:
                icon = ico
                break

        new_is_seq = data['is_sequence']
        # Add 's' to icon_name if is sequence (image -> images)
        if new_is_seq:
            icon += 's'
        data['icon'] = icon
        data['thumb'] = (
            ext in self.image_extensions
            or ext in self.video_extensions
        )
        data['prev'] = (
            ext in self.video_extensions
            or (new_is_seq and ext in self.image_extensions)
        )

        actions = []

        found = False
        if data["ext"] in self.image_extensions:
            for item in self.components_list.widgets():
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
                    paths = list(data['files'])
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
                    if data['files'] == list(item.in_data['files']):
                        found = True
                        break
                    a_name = 'merge'
                    item.add_action(a_name)
                    if a_name not in actions:
                        actions.append(a_name)

        if new_is_seq:
            actions.append('split')

        if found is False:
            new_repre = self.handle_new_repre_name(data['representation'])
            data['representation'] = new_repre
            self._add_item(data, actions)

    def handle_new_repre_name(self, repre_name):
        renamed = False
        for item in self.components_list.widgets():
            if repre_name == item.input_repre.text():
                check_regex = '_\w+$'
                result = re.findall(check_regex, repre_name)
                next_num = 2
                if len(result) == 1:
                    repre_name = repre_name.replace(result[0], '')
                    next_num = int(result[0].replace('_', ''))
                    next_num += 1
                repre_name = '{}_{}'.format(repre_name, next_num)
                renamed = True
                break
        if renamed:
            return self.handle_new_repre_name(repre_name)
        return repre_name

    def repre_name_changed(self, in_item, repre_name):
        is_valid = True
        if repre_name.strip() == '':
            in_item.set_repre_name_valid(False)
            is_valid = False
        else:
            for item in self.components_list.widgets():
                if item == in_item:
                    continue
                if item.input_repre.text() == repre_name:
                    item.set_repre_name_valid(False)
                    in_item.set_repre_name_valid(False)
                    is_valid = False
        global_valid = is_valid
        if is_valid:
            in_item.set_repre_name_valid(True)
            for item in self.components_list.widgets():
                if item.has_valid_repre:
                    continue
                self.repre_name_changed(item, item.input_repre.text())
            for item in self.components_list.widgets():
                if not item.has_valid_repre:
                    global_valid = False
                    break
        self.parent_widget.set_valid_repre_names(global_valid)

    def merge_items(self, in_item):
        self.parent_widget.working_start()
        items = []
        in_paths = in_item.in_data['files']
        paths = in_paths
        for item in self.components_list.widgets():
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
        data = {'representations' : []}
        for item in self.components_list.widgets():
            data['representations'].append(item.collect_data())
        return data
