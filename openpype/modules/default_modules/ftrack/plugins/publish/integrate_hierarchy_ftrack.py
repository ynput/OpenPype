from __future__ import print_function
from PySide2 import QtWidgets, QtCore
from pprint import pformat
from contextlib import contextmanager

# Constants
WORKFILE_START_FRAME = 1001
HIERARCHY_TEMPLATE = "shots[Folder]/{sequence}[Sequence]"
CREATE_TASK_TYPE = "Compositing"


@contextmanager
def maintained_ftrack_session():
    import ftrack_api
    import os

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
    url = os.getenv("FTRACK_SERVER")
    user = os.getenv("FTRACK_API_USER")
    api = os.getenv("FTRACK_API_KEY")

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
        self.setStyleSheet('QTreeWidget {color: #9a9a9a; background-color: #2a2a2a; alternate-background-color: #2d2d2d; font: 14px "Discreet"}'
                           'QTreeWidget::item:selected {color: #d9d9d9; background-color: #474747; border: 1px solid #111111}'
                           'QHeaderView {color: #9a9a9a; background-color: #393939; font: 14px "Discreet"}'
                           'QTreeWidget::item:selected {selection-background-color: #111111}'
                           'QMenu {color: #9a9a9a; background-color: #24303d; font: 14px "Discreet"}'
                           'QMenu::item:selected {color: #d9d9d9; background-color: #3a4551}')
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


def main_window(selection):
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

        def timecode_to_frames(_timecode, start=None):
            return _frames(_seconds(_timecode) - _seconds(start))

        if '+' in timecode:
            timecode = timecode.replace('+', ':')
        elif '#' in timecode:
            timecode = timecode.replace('#', ':')

        frames = int(round(timecode_to_frames(timecode, start='00:00:00:00')))

        return frames

    def timeline_info(selection):
        import flame

        # identificar as informacoes dos segmentos na timeline
        for sequence in selection:
            frame_rate = float(str(sequence.frame_rate)[:-4])
            for ver in sequence.versions:
                for tracks in ver.tracks:
                    for segment in tracks.segments:
                        print(segment.type)
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
                            CREATE_TASK_TYPE,  # task type
                            str(WORKFILE_START_FRAME),  # start frame
                            str(clip_duration),  # clip duration
                            "0:0",  # handles
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
        import flame
        import six
        import sys
        import re

        def create_ftrack_entity(session, type, name, parent=None):
            parent = parent or f_project
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
                type, name, f_project["id"])

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

        def get_all_task_types():
            tasks = {}
            proj_template = f_project['project_schema']
            temp_task_types = proj_template['_task_type_schema']['types']

            for type in temp_task_types:
                if type['name'] not in tasks:
                    tasks[type['name']] = type

            return tasks

        def create_task(task_type, parent):
            existing_task = [
                child for child in parent['children']
                if child.entity_type.lower() == 'task'
                if child['name'].lower() in task_type.lower()
            ]

            if existing_task:
                return existing_task

            task = session.create('Task', {
                "name": task_type.lower(),
                "parent": parent
            })
            task_types = get_all_task_types()
            task["type"] = task_types[task_type]

            return task


        # start procedure
        with maintained_ftrack_session() as session:
            print("Ftrack session is: {}".format(session))

            # get project name from flame current project
            project_name = flame.project.current_project.name

            # get project from ftrack -
            # ftrack project name has to be the same as flame project!
            query = 'Project where full_name is "{}"'.format(project_name)
            f_project = session.query(query).one()
            print("Ftrack project is: {}".format(f_project))

            # Get all selected items from treewidget
            for item in tree.selectedItems():
                # solve handle start and end
                handles = item.text(5)
                if ":" in handles:
                    _s, _e = handles.split(":")
                    handle_start = int(_s)
                    handle_end = int(_e)
                else:
                    handle_start = int(handles)
                    handle_end = int(handles)

                # frame ranges
                frame_start = int(item.text(3))
                frame_duration = int(item.text(4))
                frame_end = frame_start + frame_duration

                # description
                shot_description = item.text(6)
                task_description = item.text(7)

                # other
                task_type = item.text(2)
                shot_name = item.text(1)
                sequence_name = item.text(0)

                # populate full shot info
                shot_attributes = {
                    "sequence": sequence_name,
                    "shot": shot_name,
                    "task": task_type
                }

                # format hierarchy template
                hierarchy_text = hierarchy_template.text()
                hierarchy_text = hierarchy_text.format(**shot_attributes)
                print(hierarchy_text)

                # solve parents
                parents = generate_parents_from_template(hierarchy_text)
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
                    item.text(1),
                    _parent
                )
                print("Shot entity is: {}".format(f_s_entity))

                # create custom attributtes
                custom_attrs = {
                    "frameStart": frame_start,
                    "frameEnd": frame_end,
                    "handleStart": handle_start,
                    "handleEnd": handle_end
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
            "columnWidth": 100,
            "order": 0
        },
        "Shot name": {
            "columnWidth": 100,
            "order": 1
        },
        "Task type": {
            "columnWidth": 100,
            "order": 2
        },
        "Start frame": {
            "columnWidth": 100,
            "order": 3
        },
        "Clip duration": {
            "columnWidth": 100,
            "order": 4
        },
        "Handles": {
            "columnWidth": 100,
            "order": 5
        },
        "Shot description": {
            "columnWidth": 300,
            "order": 6
        },
        "Task description": {
            "columnWidth": 300,
            "order": 7
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

    # input fields
    hierarchy_label = FlameLabel(
        'Parents template', 'normal', window)
    hierarchy_template = FlameLineEdit(HIERARCHY_TEMPLATE, window)

    ## Button
    select_all_btn = FlameButton('Select All', select_all, window)
    ftrack_send_btn = FlameButton('Send to Ftrack', send_to_ftrack, window)

    ## Window Layout
    gridbox = QtWidgets.QGridLayout()
    gridbox.setMargin(20)
    gridbox.setHorizontalSpacing(20)
    gridbox.addWidget(hierarchy_label, 0, 0)
    gridbox.addWidget(hierarchy_template, 0, 1, 1, 4)
    gridbox.addWidget(tree, 1, 0, 5, 5)
    gridbox.addWidget(select_all_btn, 6, 3)
    gridbox.addWidget(ftrack_send_btn, 6, 4)

    window.setLayout(gridbox)
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
