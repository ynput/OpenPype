from __future__ import print_function
from PySide2 import QtWidgets, QtCore
from pprint import pformat
from contextlib import contextmanager

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

    def timeline_info(selection):
        import flame

        # identificar as informacoes dos segmentos na timeline
        for sequence in selection:
            for ver in sequence.versions:
                for tracks in ver.tracks:
                    for segment in tracks.segments:
                        # Add timeline segment to tree
                        QtWidgets.QTreeWidgetItem(tree, [
                            str(sequence.name)[1:-1],
                            str(segment.name)[1:-1],
                            'Compositing',
                            'Ready to Start',
                            'Tape: {} - Duration {}'.format(
                                segment.tape_name,
                                str(segment.record_duration)[4:-1]
                            ),
                            str(segment.comment)[1:-1]
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

        def create_ftrack_entity(session, type, name, parent):
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
            clips_info = []

            for item in tree.selectedItems():
                f_entity = create_ftrack_entity(
                    session,
                    "Shot",
                    item.text(1),
                    f_project
                )
                print("Shot entity is: {}".format(f_entity))

                tree_line = [
                    item.text(0),
                    item.text(1),
                    item.text(2),
                    item.text(3),
                    item.text(4),
                    item.text(5)
                ]
                print(tree_line)
                clips_info.append(tree_line)

            print("selected clips: {}".format(pformat(clips_info)))

    # creating ui
    window = QtWidgets.QWidget()
    window.setMinimumSize(500, 350)
    window.setWindowTitle('Sequence Shots to Ftrack')
    window.setWindowFlags(QtCore.Qt.WindowStaysOnTopHint)
    window.setAttribute(QtCore.Qt.WA_DeleteOnClose)
    window.setStyleSheet('background-color: #313131')

    # Center window in linux
    resolution = QtWidgets.QDesktopWidget().screenGeometry()
    window.move((resolution.width() / 2) - (window.frameSize().width() / 2),
                (resolution.height() / 2) - (window.frameSize().height() / 2))

    ## TreeWidget
    headers = ['Sequence Name', 'Shot Name', 'Task Type',
               'Task Status', 'Shot Description', 'Task Description']
    tree = FlameTreeWidget(headers, window)

    # Allow multiple items in tree to be selected
    tree.setSelectionMode(QtWidgets.QAbstractItemView.MultiSelection)

    # Set tree column width
    tree.setColumnWidth(0, 200)
    tree.setColumnWidth(1, 100)
    tree.setColumnWidth(2, 100)
    tree.setColumnWidth(3, 120)
    tree.setColumnWidth(4, 270)
    tree.setColumnWidth(5, 270)

    # Prevent weird characters when shrinking tree columns
    tree.setTextElideMode(QtCore.Qt.ElideNone)

    ## Button
    select_all_btn = FlameButton('Select All', select_all, window)
    copy_btn = FlameButton('Send to Ftrack', send_to_ftrack, window)

    ## Window Layout
    gridbox = QtWidgets.QGridLayout()
    gridbox.setMargin(20)
    gridbox.addWidget(tree, 1, 0, 5, 1)
    gridbox.addWidget(select_all_btn, 1, 1)
    gridbox.addWidget(copy_btn, 2, 1)

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
