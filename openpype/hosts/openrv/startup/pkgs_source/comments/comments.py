# review code
from PySide2 import QtCore, QtWidgets, QtGui

from rv.rvtypes import MinorMode
import rv.qtutils
import rv.commands


def get_cycle_frame(frame=None, frames_lookup=None, direction="next"):
    """Return nearest frame in direction in frames lookup.
    If the nearest frame in that direction does not exist then cycle
    over to the frames taking the first entry at the other end.
    Note:
        This function can return None if there are no frames to lookup in.
    Args:
        frame (int): frame to search from
        frames_lookup (list): frames to search in.
        direction (str, optional): search direction, either "next" or "prev"
            Defaults to "next".
    Returns:
        int or None: The nearest frame number in that direction or None
            if no lookup frames were passed.
    """
    if direction not in {"prev", "next"}:
        raise ValueError("Direction must be either 'next' or 'prev'. "
                         "Got: {}".format(direction))

    if not frames_lookup:
        return

    elif len(frames_lookup) == 1:
        return frames_lookup[0]

    # We require the sorting of the lookup frames because we pass e.g. the
    # result of `rv.extra_commands.findAnnotatedFrames()` as lookup frames
    # which according to its documentations states:
    # The array is not sorted and some frames may appear more than once.
    frames_lookup = list(sorted(frames_lookup))
    if direction == "next":
        # Return next nearest number or cycle to the lowest number
        return next((i for i in frames_lookup if i > frame),
                    frames_lookup[0])
    elif direction == "prev":
        # Return previous nearest number or cycle to the highest number
        return next((i for i in reversed(frames_lookup) if i < frame),
                    frames_lookup[-1])


class ReviewMenu(MinorMode):
    def __init__(self):
        MinorMode.__init__(self)
        self.init("py-ReviewMenu-mode", None, None,
                  [("OpenPype", [
                      ("_", None),  # separator
                      ("Review", self.runme, None, self._is_active)
                  ])],
                  # initialization order
                  sortKey="source_setup",
                  ordering=20)

        # spacers
        self.verticalSpacer = QtWidgets.QSpacerItem(
            20, 40,
            QtWidgets.QSizePolicy.Minimum,
            QtWidgets.QSizePolicy.Expanding
        )
        self.verticalSpacerMin = QtWidgets.QSpacerItem(
            2, 2,
            QtWidgets.QSizePolicy.Minimum,
            QtWidgets.QSizePolicy.Minimum
        )
        self.horizontalSpacer = QtWidgets.QSpacerItem(
            40, 10,
            QtWidgets.QSizePolicy.Expanding,
            QtWidgets.QSizePolicy.Minimum
        )
        self.customDockWidget = QtWidgets.QWidget()

        # data
        self.current_loaded_viewnode = None
        self.review_main_layout = QtWidgets.QVBoxLayout()
        self.rev_head_label = QtWidgets.QLabel("Shot Review")
        self.set_item_font(self.rev_head_label, size=16)
        self.current_loaded_shot = QtWidgets.QLabel("")
        self.current_shot_comment = QtWidgets.QPlainTextEdit()
        self.current_shot_comment.setStyleSheet(
            "color: white; background-color: black"
        )

        self.review_main_layout_head = QtWidgets.QVBoxLayout()
        self.review_main_layout_head.addWidget(self.rev_head_label)
        self.review_main_layout_head.addWidget(self.current_loaded_shot)
        self.review_main_layout_head.addWidget(self.current_shot_comment)

        self.remove_cmnt_btn = QtWidgets.QPushButton("Remove comment")  # noqa
        self.review_main_layout_head.addWidget(self.remove_cmnt_btn)

        self.rvWindow = None
        self.dockWidget = None

        # annotations controls
        self.notes_layout = QtWidgets.QVBoxLayout()
        self.notes_layout_label = QtWidgets.QLabel("Annotations")
        self.btn_note_prev = QtWidgets.QPushButton("Previous Annotation")
        self.btn_note_next = QtWidgets.QPushButton("Next Annotation")
        self.notes_layout.addWidget(self.notes_layout_label)
        self.notes_layout.addWidget(self.btn_note_prev)
        self.notes_layout.addWidget(self.btn_note_next)

        self.review_main_layout.addLayout(self.review_main_layout_head)
        self.review_main_layout.addLayout(self.notes_layout)
        self.review_main_layout.addStretch(1)
        self.customDockWidget.setLayout(self.review_main_layout)

        # signals noqa
        self.current_shot_comment.textChanged.connect(self.comment_update)
        self.remove_cmnt_btn.clicked.connect(self.clean_cmnt)
        self.btn_note_prev.clicked.connect(self.annotate_prev)
        self.btn_note_next.clicked.connect(self.annotate_next)

    def runme(self, arg1=None, arg2=None):
        self.rvWindow = rv.qtutils.sessionWindow()
        if self.dockWidget is None:
            # Create DockWidget and add the Custom Widget on first run
            self.dockWidget = QtWidgets.QDockWidget("OpenPype Review",
                                                    self.rvWindow)
            self.dockWidget.setWidget(self.customDockWidget)

            # Dock widget to the RV MainWindow
            self.rvWindow.addDockWidget(QtCore.Qt.RightDockWidgetArea,
                                        self.dockWidget)

            self.setup_listeners()
        else:
            # Toggle visibility state
            self.dockWidget.toggleViewAction().trigger()

    def _is_active(self):
        if self.dockWidget is not None and self.dockWidget.isVisible():
            return rv.commands.CheckedMenuState
        else:
            return rv.commands.UncheckedMenuState

    def set_item_font(self, item, size=14, noweight=False, bold=True):
        font = QtGui.QFont()
        if bold:
            font.setFamily("Arial Bold")
        else:
            font.setFamily("Arial")
        font.setPointSize(size)
        font.setBold(True)
        if not noweight:
            font.setWeight(75)
        item.setFont(font)

    def setup_listeners(self):
        # Some other supported signals:
        # new-source
        # graph-state-change,
        # after-progressive-loading,
        # media-relocated
        rv.commands.bind("default", "global", "source-media-set",
                         self.graph_change, "Doc string")
        rv.commands.bind("default", "global", "after-graph-view-change",
                         self.graph_change, "Doc string")

    def graph_change(self, event):
        # update the view
        self.get_view_source()

    def get_view_source(self):
        sources = rv.commands.sourcesAtFrame(rv.commands.frame())
        self.current_loaded_viewnode = sources[0] if sources else None
        self.update_ui_attribs()

    def update_ui_attribs(self):
        node = self.current_loaded_viewnode

        # Use namespace as loaded shot label
        namespace = ""
        if node is not None:
            property_name = "{}.openpype.namespace".format(node)
            if rv.commands.propertyExists(property_name):
                namespace = rv.commands.getStringProperty(property_name)[0]

        self.current_loaded_shot.setText(namespace)

        self.setup_properties()

    def comment_update(self):
        node = rv.commands.nodesOfType('RVFileSource')[0]
        if node is None:
            return

        comment = self.current_shot_comment.toPlainText()
        att_prop = "{0}.openpype_review.comment".format(node)
        rv.commands.newProperty(att_prop, rv.commands.StringType, 1)
        rv.commands.setStringProperty(att_prop, [str(comment)], True)

    def clean_cmnt(self):
        attribs = []
        node = rv.commands.nodesOfType('RVFileSource')[0]
        if node is None:
            return
        att_prop_cmnt = node + ".openpype_review.comment"
        attribs.append(att_prop_cmnt)

        for prop in attribs:
            if not rv.commands.propertyExists(prop):
                rv.commands.newProperty(prop, rv.commands.StringType, 1)
            rv.commands.setStringProperty(prop, [""], True)

        self.current_shot_comment.setPlainText("")

    def annotate_next(self):
        """Set frame to next annotated frame"""
        all_notes = self.get_annotated_for_view()
        if not all_notes:
            return
        nxt = get_cycle_frame(frame=rv.commands.frame(),
                              frames_lookup=all_notes,
                              direction="next")

        rv.commands.setFrame(int(nxt))
        rv.commands.redraw()

    def annotate_prev(self):
        """Set frame to previous annotated frame"""
        all_notes = self.get_annotated_for_view()
        if not all_notes:
            return
        previous = get_cycle_frame(frame=rv.commands.frame(),
                                   frames_lookup=all_notes,
                                   direction="prev")
        rv.commands.setFrame(int(previous))
        rv.commands.redraw()

    def get_annotated_for_view(self):
        """Return the frame numbers for all annotated frames"""
        annotated_frames = rv.extra_commands.findAnnotatedFrames()
        return annotated_frames


def createMode():
    return ReviewMenu()
