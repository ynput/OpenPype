from __future__ import print_function
import os
from PySide2 import QtWidgets, QtCore
from pprint import pformat
from contextlib import contextmanager
from xml.etree import ElementTree as ET
import ConfigParser as CP
import io

# Fill following constants or set them via environment variable
FTRACK_MODULE_PATH = None
FTRACK_API_KEY = None
FTRACK_API_USER = None
FTRACK_SERVER = None

SCRIPT_DIR = os.path.dirname(__file__)
EXPORT_PRESETS_DIR = os.path.join(SCRIPT_DIR, "export_preset")
CONFIG_DIR = os.path.join(os.path.expanduser(
    "~/.openpype"), "openpype_flame_to_ftrack")


def import_ftrack_api():
    try:
        import ftrack_api
        return ftrack_api
    except ImportError:
        import sys
        ftrk_m_p = FTRACK_MODULE_PATH or os.getenv("FTRACK_MODULE_PATH")
        sys.path.append(ftrk_m_p)
        import ftrack_api
        return ftrack_api


@contextmanager
def maintained_ftrack_session():
    import os
    ftrack_api = import_ftrack_api()

    def validate_credentials(url, user, api):
        first_validation = True
        if not user:
            print('- Ftrack Username is not set')
            first_validation = False
        if not api:
            print('- Ftrack API key is not set')
            first_validation = False
        if not first_validation:
            return False

        try:
            session = ftrack_api.Session(
                server_url=url,
                api_user=user,
                api_key=api
            )
            session.close()
        except Exception as _e:
            print(
                "Can't log into Ftrack with used credentials: {}".format(
                    _e)
            )
            ftrack_cred = {
                'Ftrack server': str(url),
                'Username': str(user),
                'API key': str(api),
            }

            item_lens = [len(key) + 1 for key in ftrack_cred]
            justify_len = max(*item_lens)
            for key, value in ftrack_cred.items():
                print('{} {}'.format((key + ':').ljust(
                    justify_len, ' '), value))
            return False
        print(
            'Credentials Username: "{}", API key: "{}" are valid.'.format(
                user, api)
        )
        return True

    # fill your own credentials
    url = FTRACK_SERVER or os.getenv("FTRACK_SERVER") or ""
    user = FTRACK_API_USER or os.getenv("FTRACK_API_USER") or ""
    api = FTRACK_API_KEY or os.getenv("FTRACK_API_KEY") or ""

    try:
        assert validate_credentials(url, user, api), (
            "Ftrack credentials failed")
        # open ftrack session
        session = ftrack_api.Session(
            server_url=url,
            api_user=user,
            api_key=api
        )
        yield session
    except Exception as _E:
        print(
            "ERROR: {}".format(_E))
    finally:
        # close the session
        session.close()


@contextmanager
def make_temp_dir():
    import tempfile
    import shutil

    try:
        dirpath = tempfile.mkdtemp()

        yield dirpath

    except IOError as _error:
        raise IOError("Not able to create temp dir file: {}".format(_error))

    finally:
        print(dirpath)
        shutil.rmtree(dirpath)


@contextmanager
def get_config(section=None):
    cfg_file_path = os.path.join(CONFIG_DIR, "settings.ini")

    # create config dir
    if not os.path.exists(CONFIG_DIR):
        print("making dirs at: `{}`".format(CONFIG_DIR))
        os.makedirs(CONFIG_DIR, mode=0o777)

    # write default data to settings.ini
    if not os.path.exists(cfg_file_path):
        default_cfg = cfg_default()
        config = CP.RawConfigParser()
        config.readfp(io.BytesIO(default_cfg))
        with open(cfg_file_path, 'wb') as cfg_file:
            config.write(cfg_file)

    try:
        config = CP.RawConfigParser()
        config.read(cfg_file_path)
        if section:
            _cfg_data = {
                k: v
                for s in config.sections()
                for k, v in config.items(s)
                if s == section
            }
        else:
            _cfg_data = {s: dict(config.items(s)) for s in config.sections()}

        yield _cfg_data

    except IOError as _error:
        raise IOError('Not able to read settings.ini file: {}'.format(_error))

    finally:
        pass


def set_config(cfg_data, section=None):
    cfg_file_path = os.path.join(CONFIG_DIR, "settings.ini")

    config = CP.RawConfigParser()
    config.read(cfg_file_path)

    try:
        if not section:
            for section in cfg_data:
                for key, value in cfg_data[section].items():
                    config.set(section, key, value)
        else:
            for key, value in cfg_data.items():
                config.set(section, key, value)

        with open(cfg_file_path, 'wb') as cfg_file:
            config.write(cfg_file)

    except IOError as _error:
        raise IOError('Not able to write settings.ini file: {}'.format(_error))


def cfg_default():
    return """
[main]
workfile_start_frame = 1001
shot_handles = 0
shot_name_template = {sequence}_{shot}
hierarchy_template = shots[Folder]/{sequence}[Sequence]
create_task_type = Compositing
source_resolution = 0
"""


def get_all_task_types(project_entity):
    tasks = {}
    proj_template = project_entity['project_schema']
    temp_task_types = proj_template['_task_type_schema']['types']

    for type in temp_task_types:
        if type['name'] not in tasks:
            tasks[type['name']] = type

    return tasks


def export_thumbnail(sequence, tempdir_path):
    import flame
    export_preset = os.path.join(
        EXPORT_PRESETS_DIR,
        "openpype_seg_thumbnails_jpg.xml"
    )
    poster_frame_exporter = flame.PyExporter()
    poster_frame_exporter.foreground = True
    poster_frame_exporter.export(sequence, export_preset, tempdir_path)


def export_video(sequence, tempdir_path):
    import flame
    export_preset = os.path.join(
        EXPORT_PRESETS_DIR,
        "openpype_seg_video_h264.xml"
    )
    poster_frame_exporter = flame.PyExporter()
    poster_frame_exporter.foreground = True
    poster_frame_exporter.export(sequence, export_preset, tempdir_path)


def timecode_to_frames(timecode, framerate):
    def _seconds(value):
        if isinstance(value, str):
            _zip_ft = zip((3600, 60, 1, 1 / framerate), value.split(':'))
            return sum(f * float(t) for f, t in _zip_ft)
        elif isinstance(value, (int, float)):
            return value / framerate
        return 0

    def _frames(seconds):
        return seconds * framerate

    def tc_to_frames(_timecode, start=None):
        return _frames(_seconds(_timecode) - _seconds(start))

    if '+' in timecode:
        timecode = timecode.replace('+', ':')
    elif '#' in timecode:
        timecode = timecode.replace('#', ':')

    frames = int(round(tc_to_frames(timecode, start='00:00:00:00')))

    return frames


class FlameLabel(QtWidgets.QLabel):
    """
    Custom Qt Flame Label Widget

    For different label looks set label_type as: 'normal', 'background', or 'outline'

    To use:

    label = FlameLabel('Label Name', 'normal', window)
    """

    def __init__(self, label_name, label_type, parent_window, *args, **kwargs):
        super(FlameLabel, self).__init__(*args, **kwargs)

        self.setText(label_name)
        self.setParent(parent_window)
        self.setMinimumSize(130, 28)
        self.setMaximumHeight(28)
        self.setFocusPolicy(QtCore.Qt.NoFocus)

        # Set label stylesheet based on label_type

        if label_type == 'normal':
            self.setStyleSheet('QLabel {color: #9a9a9a; border-bottom: 1px inset #282828; font: 14px "Discreet"}'
                               'QLabel:disabled {color: #6a6a6a}')
        elif label_type == 'background':
            self.setAlignment(QtCore.Qt.AlignCenter)
            self.setStyleSheet(
                'color: #9a9a9a; background-color: #393939; font: 14px "Discreet"')
        elif label_type == 'outline':
            self.setAlignment(QtCore.Qt.AlignCenter)
            self.setStyleSheet(
                'color: #9a9a9a; background-color: #212121; border: 1px solid #404040; font: 14px "Discreet"')


class FlameLineEdit(QtWidgets.QLineEdit):
    """
    Custom Qt Flame Line Edit Widget

    Main window should include this: window.setFocusPolicy(QtCore.Qt.StrongFocus)

    To use:

    line_edit = FlameLineEdit('Some text here', window)
    """

    def __init__(self, text, parent_window, *args, **kwargs):
        super(FlameLineEdit, self).__init__(*args, **kwargs)

        self.setText(text)
        self.setParent(parent_window)
        self.setMinimumHeight(28)
        self.setMinimumWidth(110)
        self.setStyleSheet('QLineEdit {color: #9a9a9a; background-color: #373e47; selection-color: #262626; selection-background-color: #b8b1a7; font: 14px "Discreet"}'
                           'QLineEdit:focus {background-color: #474e58}'
                           'QLineEdit:disabled {color: #6a6a6a; background-color: #373737}')


class FlameTreeWidget(QtWidgets.QTreeWidget):
    """
    Custom Qt Flame Tree Widget

    To use:

    tree_headers = ['Header1', 'Header2', 'Header3', 'Header4']
    tree = FlameTreeWidget(tree_headers, window)
    """

    def __init__(self, tree_headers, parent_window, *args, **kwargs):
        super(FlameTreeWidget, self).__init__(*args, **kwargs)

        self.setMinimumWidth(1000)
        self.setMinimumHeight(300)
        self.setSortingEnabled(True)
        self.sortByColumn(0, QtCore.Qt.AscendingOrder)
        self.setAlternatingRowColors(True)
        self.setFocusPolicy(QtCore.Qt.NoFocus)
        self.setStyleSheet(
            'QTreeWidget {color: #9a9a9a; background-color: #2a2a2a; alternate-background-color: #2d2d2d; font: 14px "Discreet"}'
            'QTreeWidget::item:selected {color: #d9d9d9; background-color: #474747; border: 1px solid #111111}'
            'QHeaderView {color: #9a9a9a; background-color: #393939; font: 14px "Discreet"}'
            'QTreeWidget::item:selected {selection-background-color: #111111}'
            'QMenu {color: #9a9a9a; background-color: #24303d; font: 14px "Discreet"}'
            'QMenu::item:selected {color: #d9d9d9; background-color: #3a4551}'
        )
        self.verticalScrollBar().setStyleSheet('color: #818181')
        self.horizontalScrollBar().setStyleSheet('color: #818181')
        self.setHeaderLabels(tree_headers)


class FlameButton(QtWidgets.QPushButton):
    """
    Custom Qt Flame Button Widget

    To use:

    button = FlameButton('Button Name', do_this_when_pressed, window)
    """

    def __init__(self, button_name, do_when_pressed, parent_window, *args, **kwargs):
        super(FlameButton, self).__init__(*args, **kwargs)

        self.setText(button_name)
        self.setParent(parent_window)
        self.setMinimumSize(QtCore.QSize(110, 28))
        self.setMaximumSize(QtCore.QSize(110, 28))
        self.setFocusPolicy(QtCore.Qt.NoFocus)
        self.clicked.connect(do_when_pressed)
        self.setStyleSheet('QPushButton {color: #9a9a9a; background-color: #424142; border-top: 1px inset #555555; border-bottom: 1px inset black; font: 14px "Discreet"}'
                           'QPushButton:pressed {color: #d9d9d9; background-color: #4f4f4f; border-top: 1px inset #666666; font: italic}'
                           'QPushButton:disabled {color: #747474; background-color: #353535; border-top: 1px solid #444444; border-bottom: 1px solid #242424}')


class FlamePushButton(QtWidgets.QPushButton):
    """
    Custom Qt Flame Push Button Widget

    To use:

    pushbutton = FlamePushButton(' Button Name', True_or_False, window)
    """

    def __init__(self, button_name, button_checked, parent_window, *args, **kwargs):
        super(FlamePushButton, self).__init__(*args, **kwargs)

        self.setText(button_name)
        self.setParent(parent_window)
        self.setCheckable(True)
        self.setChecked(button_checked)
        self.setMinimumSize(155, 28)
        self.setMaximumSize(155, 28)
        self.setFocusPolicy(QtCore.Qt.NoFocus)
        self.setStyleSheet('QPushButton {color: #9a9a9a; background-color: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 0, stop: .93 #424142, stop: .94 #2e3b48); text-align: left; border-top: 1px inset #555555; border-bottom: 1px inset black; font: 14px "Discreet"}'
                           'QPushButton:checked {color: #d9d9d9; background-color: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 0, stop: .93 #4f4f4f, stop: .94 #5a7fb4); font: italic; border: 1px inset black; border-bottom: 1px inset #404040; border-right: 1px inset #404040}'
                           'QPushButton:disabled {color: #6a6a6a; background-color: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 0, stop: .93 #383838, stop: .94 #353535); font: light; border-top: 1px solid #575757; border-bottom: 1px solid #242424; border-right: 1px solid #353535; border-left: 1px solid #353535}'
                           'QToolTip {color: black; background-color: #ffffde; border: black solid 1px}')


class FlamePushButtonMenu(QtWidgets.QPushButton):
    """
    Custom Qt Flame Menu Push Button Widget

    To use:

    push_button_menu_options = ['Item 1', 'Item 2', 'Item 3', 'Item 4']
    menu_push_button = FlamePushButtonMenu('push_button_name', push_button_menu_options, window)

    or

    push_button_menu_options = ['Item 1', 'Item 2', 'Item 3', 'Item 4']
    menu_push_button = FlamePushButtonMenu(push_button_menu_options[0], push_button_menu_options, window)
    """

    def __init__(self, button_name, menu_options, parent_window, *args, **kwargs):
        super(FlamePushButtonMenu, self).__init__(*args, **kwargs)
        from functools import partial

        self.setText(button_name)
        self.setParent(parent_window)
        self.setMinimumHeight(28)
        self.setMinimumWidth(110)
        self.setFocusPolicy(QtCore.Qt.NoFocus)
        self.setStyleSheet('QPushButton {color: #9a9a9a; background-color: #24303d; font: 14px "Discreet"}'
                           'QPushButton:disabled {color: #747474; background-color: #353535; border-top: 1px solid #444444; border-bottom: 1px solid #242424}')

        def create_menu(option):
            self.setText(option)

        pushbutton_menu = QtWidgets.QMenu(parent_window)
        pushbutton_menu.setFocusPolicy(QtCore.Qt.NoFocus)
        pushbutton_menu.setStyleSheet('QMenu {color: #9a9a9a; background-color:#24303d; font: 14px "Discreet"}'
                                      'QMenu::item:selected {color: #d9d9d9; background-color: #3a4551}')
        for option in menu_options:
            pushbutton_menu.addAction(option, partial(create_menu, option))

        self.setMenu(pushbutton_menu)


def main_window(selection):
    import flame
    import six
    import sys
    import re

    def timeline_info(selection):
        # identificar as informacoes dos segmentos na timeline
        for sequence in selection:
            frame_rate = float(str(sequence.frame_rate)[:-4])
            for ver in sequence.versions:
                for tracks in ver.tracks:
                    for segment in tracks.segments:
                        print(segment.attributes)
                        # get clip frame duration
                        record_duration = str(segment.record_duration)[1:-1]
                        clip_duration = timecode_to_frames(
                            record_duration, frame_rate)

                        # populate shot source metadata
                        shot_description = ""
                        for attr in ["tape_name", "source_name", "head",
                                     "tail", "file_path"]:
                            if not hasattr(segment, attr):
                                continue
                            _value = getattr(segment, attr)
                            _label = attr.replace("_", " ").capitalize()
                            row = "{}: {}\n".format(_label, _value)
                            shot_description += row

                        # Add timeline segment to tree
                        QtWidgets.QTreeWidgetItem(tree, [
                            str(sequence.name)[1:-1],  # seq
                            str(segment.name)[1:-1],  # shot
                            str(clip_duration),  # clip duration
                            shot_description,  # shot description
                            str(segment.comment)[1:-1]  # task description
                        ]).setFlags(
                            QtCore.Qt.ItemIsEditable
                            | QtCore.Qt.ItemIsEnabled
                            | QtCore.Qt.ItemIsSelectable
                        )

        # Select top item in tree
        tree.setCurrentItem(tree.topLevelItem(0))

    def select_all():

        tree.selectAll()

    def send_to_ftrack():
        def create_ftrack_entity(session, type, name, parent=None):
            parent = parent or F_PROJ_ENTITY
            entity = session.create(type, {
                'name': name,
                'parent': parent
            })
            try:
                session.commit()
            except Exception:
                tp, value, tb = sys.exc_info()
                session.rollback()
                session._configure_locations()
                six.reraise(tp, value, tb)
            return entity

        def get_ftrack_entity(session, type, name, parent):
            query = '{} where name is "{}" and project_id is "{}"'.format(
                type, name, F_PROJ_ENTITY["id"])

            try:
                entity = session.query(query).one()
            except Exception:
                entity = None

            # if entity doesnt exist then create one
            if not entity:
                entity = create_ftrack_entity(
                    session,
                    type,
                    name,
                    parent
                )

            return entity

        def generate_parents_from_template(template):
            parents = []
            t_split = template.split("/")
            replace_patern = re.compile(r"(\[.*\])")
            type_patern = re.compile(r"\[(.*)\]")

            for t_s in t_split:
                match_type = type_patern.findall(t_s)
                if not match_type:
                    raise Exception((
                        "Missing correct type flag in : {}"
                        "/n Example: name[Type]").format(
                            t_s)
                    )
                new_name = re.sub(replace_patern, "", t_s)
                f_type = match_type.pop()

                parents.append((new_name, f_type))

            return parents

        def create_task(task_type, parent):
            existing_task = [
                child for child in parent['children']
                if child.entity_type.lower() == 'task'
                if child['name'].lower() in task_type.lower()
            ]

            if existing_task:
                return existing_task.pop()

            task = session.create('Task', {
                "name": task_type.lower(),
                "parent": parent
            })
            task["type"] = F_PROJ_TASK_TYPES[task_type]

            return task

        '''
        ##################### start procedure
        '''
        # resolve active project and add it to F_PROJ_ENTITY
        if proj_selector:
            selected_project_name = project_select_input.text()
            F_PROJ_ENTITY = next(
                (p for p in all_projects
                 if p["full_name"] is selected_project_name),
                None
            )

        _cfg_data_back = {}

        # get shot name template from gui input
        shot_name_template = shot_name_template_input.text()

        # get hierarchy from gui input
        hierarchy_text = hierarchy_template_input.text()

        # get hanldes from gui input
        handles = handles_input.text()

        # get frame start from gui input
        frame_start = int(start_frame_input.text())

        # get task type from gui input
        task_type = task_type_input.text()

        # get resolution from gui inputs
        width = width_input.text()
        height = height_input.text()
        pixel_aspect = pixel_aspect_input.text()
        fps = fps_input.text()

        _cfg_data_back = {
            "shot_name_template": shot_name_template,
            "workfile_start_frame": str(frame_start),
            "shot_handles": handles,
            "hierarchy_template": hierarchy_text,
            "create_task_type": task_type,
            "source_resolution": (
                "1" if source_resolution_btn.isChecked() else "0")
        }

        # add cfg data back to settings.ini
        set_config(_cfg_data_back, "main")

        with maintained_ftrack_session() as session, \
                make_temp_dir() as tempdir_path:
            print("tempdir_path: {}".format(tempdir_path))
            print("Ftrack session is: {}".format(session))

            for seq in selection:
                export_thumbnail(seq, tempdir_path)
                export_video(seq, tempdir_path)
                break

            temp_files = os.listdir(tempdir_path)
            thumbnails = [f for f in temp_files if "jpg" in f]
            videos = [f for f in temp_files if "mov" in f]

            print(temp_files)
            print(thumbnails)
            print(videos)

            # Get all selected items from treewidget
            for item in tree.selectedItems():
                # frame ranges
                frame_duration = int(item.text(2))
                frame_end = frame_start + frame_duration

                # description
                shot_description = item.text(3)
                task_description = item.text(4)

                # other
                sequence_name = item.text(0)
                shot_name = item.text(1)

                # get component files
                thumb_f = next((f for f in thumbnails if shot_name in f), None)
                video_f = next((f for f in videos if shot_name in f), None)
                print(thumb_f)
                print(video_f)

                thumb_fp = os.path.join(tempdir_path, thumb_f)
                video_fp = os.path.join(tempdir_path, video_f)
                print(thumb_fp)
                print(video_fp)

                # populate full shot info
                shot_attributes = {
                    "sequence": sequence_name,
                    "shot": shot_name,
                    "task": task_type
                }

                # format shot name template
                _shot_name = shot_name_template.format(**shot_attributes)

                # format hierarchy template
                _hierarchy_text = hierarchy_text.format(**shot_attributes)
                print(_hierarchy_text)

                # solve parents
                parents = generate_parents_from_template(_hierarchy_text)
                print(parents)

                # obtain shot parents entities
                _parent = None
                for _name, _type in parents:
                    p_entity = get_ftrack_entity(
                        session,
                        _type,
                        _name,
                        _parent
                    )
                    print(p_entity)
                    _parent = p_entity

                # obtain shot ftrack entity
                f_s_entity = get_ftrack_entity(
                    session,
                    "Shot",
                    _shot_name,
                    _parent
                )
                print("Shot entity is: {}".format(f_s_entity))

                # create custom attributtes
                custom_attrs = {
                    "frameStart": frame_start,
                    "frameEnd": frame_end,
                    "handleStart": int(handles),
                    "handleEnd": int(handles),
                    "resolutionWidth": int(width),
                    "resolutionHeight": int(height),
                    "pixelAspect": float(pixel_aspect),
                    "fps": float(fps)
                }

                # update custom attributes on shot entity
                for key in custom_attrs:
                    f_s_entity['custom_attributes'][key] = custom_attrs[key]

                task_entity = create_task(task_type, f_s_entity)

                # Create notes.
                user = session.query(
                    "User where username is \"{}\"".format(session.api_user)
                ).first()

                f_s_entity.create_note(shot_description, author=user)

                if task_description:
                    task_entity.create_note(task_description, user)

                try:
                    session.commit()
                except Exception:
                    tp, value, tb = sys.exc_info()
                    session.rollback()
                    session._configure_locations()
                    six.reraise(tp, value, tb)

    # creating ui
    window = QtWidgets.QWidget()
    window.setMinimumSize(1500, 600)
    window.setWindowTitle('Sequence Shots to Ftrack')
    window.setWindowFlags(QtCore.Qt.WindowStaysOnTopHint)
    window.setAttribute(QtCore.Qt.WA_DeleteOnClose)
    window.setStyleSheet('background-color: #313131')

    # Center window in linux
    resolution = QtWidgets.QDesktopWidget().screenGeometry()
    window.move((resolution.width() / 2) - (window.frameSize().width() / 2),
                (resolution.height() / 2) - (window.frameSize().height() / 2))

    # TreeWidget
    columns = {
        "Sequence name": {
            "columnWidth": 200,
            "order": 0
        },
        "Shot name": {
            "columnWidth": 200,
            "order": 1
        },
        "Clip duration": {
            "columnWidth": 100,
            "order": 2
        },
        "Shot description": {
            "columnWidth": 500,
            "order": 3
        },
        "Task description": {
            "columnWidth": 500,
            "order": 4
        },
    }
    ordered_column_labels = columns.keys()
    for _name, _value in columns.items():
        ordered_column_labels.pop(_value["order"])
        ordered_column_labels.insert(_value["order"], _name)

    print(ordered_column_labels)

    tree = FlameTreeWidget(ordered_column_labels, window)

    # Allow multiple items in tree to be selected
    tree.setSelectionMode(QtWidgets.QAbstractItemView.MultiSelection)

    # Set tree column width
    for _name, _val in columns.items():
        tree.setColumnWidth(
            _val["order"],
            _val["columnWidth"]
        )

    # Prevent weird characters when shrinking tree columns
    tree.setTextElideMode(QtCore.Qt.ElideNone)

    with maintained_ftrack_session() as _session, get_config("main") as cfg_d:

        for select in selection:
            seq_height = select.height
            seq_width = select.width
            fps = float(str(select.frame_rate)[:-4])
            break

        # input fields
        shot_name_label = FlameLabel(
            'Shot name template', 'normal', window)
        shot_name_template_input = FlameLineEdit(
            cfg_d["shot_name_template"], window)

        hierarchy_label = FlameLabel(
            'Parents template', 'normal', window)
        hierarchy_template_input = FlameLineEdit(
            cfg_d["hierarchy_template"], window)

        start_frame_label = FlameLabel(
            'Workfile start frame', 'normal', window)
        start_frame_input = FlameLineEdit(
            cfg_d["workfile_start_frame"], window)

        handles_label = FlameLabel(
            'Shot handles', 'normal', window)
        handles_input = FlameLineEdit(cfg_d["shot_handles"], window)

        source_resolution_btn = FlamePushButton(
            'Source resolutuion', bool(int(cfg_d["source_resolution"])),
            window
        )
        width_label = FlameLabel(
            'Sequence width', 'normal', window)
        width_input = FlameLineEdit(str(seq_width), window)

        height_label = FlameLabel(
            'Sequence height', 'normal', window)
        height_input = FlameLineEdit(str(seq_height), window)

        pixel_aspect_label = FlameLabel(
            'Pixel aspect ratio', 'normal', window)
        pixel_aspect_input = FlameLineEdit(str(1.00), window)

        fps_label = FlameLabel(
            'Frame rate', 'normal', window)
        fps_input = FlameLineEdit(str(fps), window)

        # get project name from flame current project
        project_name = flame.project.current_project.name

        # get project from ftrack -
        # ftrack project name has to be the same as flame project!
        query = 'Project where full_name is "{}"'.format(project_name)

        # globally used variables
        F_PROJ_ENTITY = _session.query(query).one()

        proj_selector = bool(not F_PROJ_ENTITY)

        if proj_selector:
            all_projects = _session.query(
                "Project where status is active").all()
            F_PROJ_ENTITY = all_projects[0]
            project_names = [p["full_name"] for p in all_projects]
            project_select_label = FlameLabel(
                'Select Ftrack project', 'normal', window)
            project_select_input = FlamePushButtonMenu(
                F_PROJ_ENTITY["full_name"], project_names, window)

        F_PROJ_TASK_TYPES = get_all_task_types(F_PROJ_ENTITY)

        task_type_label = FlameLabel(
            'Create Task (type)', 'normal', window)
        task_type_input = FlamePushButtonMenu(
            cfg_d["create_task_type"], F_PROJ_TASK_TYPES, window)

        # Button
        select_all_btn = FlameButton('Select All', select_all, window)
        ftrack_send_btn = FlameButton('Send to Ftrack', send_to_ftrack, window)

        # left props
        v_shift = 0
        prop_layout_l = QtWidgets.QGridLayout()
        prop_layout_l.setHorizontalSpacing(30)
        if proj_selector:
            prop_layout_l.addWidget(project_select_label, v_shift, 0)
            prop_layout_l.addWidget(project_select_input, v_shift, 1)
            v_shift += 1
        prop_layout_l.addWidget(shot_name_label, (v_shift + 0), 0)
        prop_layout_l.addWidget(shot_name_template_input, (v_shift + 0), 1)
        prop_layout_l.addWidget(hierarchy_label, (v_shift + 1), 0)
        prop_layout_l.addWidget(hierarchy_template_input, (v_shift + 1), 1)
        prop_layout_l.addWidget(start_frame_label, (v_shift + 2), 0)
        prop_layout_l.addWidget(start_frame_input, (v_shift + 2), 1)
        prop_layout_l.addWidget(handles_label, (v_shift + 3), 0)
        prop_layout_l.addWidget(handles_input, (v_shift + 3), 1)
        prop_layout_l.addWidget(task_type_label, (v_shift + 4), 0)
        prop_layout_l.addWidget(task_type_input, (v_shift + 4), 1)

        # right props
        prop_widget_r = QtWidgets.QWidget(window)
        prop_layout_r = QtWidgets.QGridLayout(prop_widget_r)
        prop_layout_r.setHorizontalSpacing(30)
        prop_layout_r.setAlignment(
            QtCore.Qt.AlignLeft | QtCore.Qt.AlignTop)
        prop_layout_r.setContentsMargins(0, 0, 0, 0)
        prop_layout_r.addWidget(source_resolution_btn, 0, 0)
        prop_layout_r.addWidget(width_label, 1, 0)
        prop_layout_r.addWidget(width_input, 1, 1)
        prop_layout_r.addWidget(height_label, 2, 0)
        prop_layout_r.addWidget(height_input, 2, 1)
        prop_layout_r.addWidget(pixel_aspect_label, 3, 0)
        prop_layout_r.addWidget(pixel_aspect_input, 3, 1)
        prop_layout_r.addWidget(fps_label, 4, 0)
        prop_layout_r.addWidget(fps_input, 4, 1)

        # prop layout
        prop_main_layout = QtWidgets.QHBoxLayout()
        prop_main_layout.addLayout(prop_layout_l, 1)
        prop_main_layout.addSpacing(20)
        prop_main_layout.addWidget(prop_widget_r, 1)

        # buttons layout
        hbox = QtWidgets.QHBoxLayout()
        hbox.addWidget(select_all_btn)
        hbox.addWidget(ftrack_send_btn)

        # put all layouts together
        main_frame = QtWidgets.QVBoxLayout(window)
        main_frame.setMargin(20)
        main_frame.addLayout(prop_main_layout)
        main_frame.addWidget(tree)
        main_frame.addLayout(hbox)

        window.show()

        timeline_info(selection)

    return window


def scope_sequence(selection):
    import flame
    return any(isinstance(item, flame.PySequence) for item in selection)


def get_media_panel_custom_ui_actions():
    return [
        {
            "name": "OpenPype: Ftrack",
            "actions": [
                {
                    "name": "Create Shots",
                    "isVisible": scope_sequence,
                    "execute": main_window
                }
            ]
        }
    ]
