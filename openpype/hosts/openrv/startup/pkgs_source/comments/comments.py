# review code
import os
import sys
from PySide2 import QtWidgets, QtGui
from PySide2.QtCore import QRect
from PySide2.QtWidgets import QApplication

from rv.qtutils import *
from rv.rvtypes import *

from rv.commands import *
from rv.extra_commands import *


class ReviewMenu(MinorMode):
    def __init__(self):
        MinorMode.__init__(self)
        self.init("py-ReviewMenu-mode", None, None, [("-= OpenPype =-", [("Review", self.runme, None, None)])])

        # spacers
        self.verticalSpacer = QtWidgets.QSpacerItem(20, 40, QtWidgets.QSizePolicy.Minimum,
                                                    QtWidgets.QSizePolicy.Expanding)
        self.verticalSpacerMin = QtWidgets.QSpacerItem(2, 2, QtWidgets.QSizePolicy.Minimum,
                                                       QtWidgets.QSizePolicy.Minimum)
        self.horizontalSpacer = QtWidgets.QSpacerItem(40, 10, QtWidgets.QSizePolicy.Expanding,
                                                      QtWidgets.QSizePolicy.Minimum)
        self.customDockWidget = QtWidgets.QWidget()

        # data
        self.current_loaded_viewnode = None
        self.review_main_layout = QtWidgets.QVBoxLayout()
        self.rev_head_label = QtWidgets.QLabel("Shot Review")
        self.set_item_font(self.rev_head_label, size=16)
        self.rev_head_name = QtWidgets.QLabel("Shot Name")
        self.current_loaded_shot = QtWidgets.QLabel("")
        self.current_shot_status = QtWidgets.QComboBox()
        self.current_shot_status.addItems(["In Review", "Ready For Review", "Reviewed", "Approved", "Deliver"])
        self.current_shot_comment = QtWidgets.QPlainTextEdit()
        self.current_shot_comment.setStyleSheet("color: white;  background-color: black")

        self.review_main_layout_head = QtWidgets.QVBoxLayout()
        self.review_main_layout_head.addWidget(self.rev_head_label)
        self.review_main_layout_head.addWidget(self.rev_head_name)
        self.review_main_layout_head.addWidget(self.current_loaded_shot)
        self.review_main_layout_head.addWidget(self.current_shot_status)
        self.review_main_layout_head.addWidget(self.current_shot_comment)

        self.get_view_image = QtWidgets.QPushButton("Get image")
        self.review_main_layout_head.addWidget(self.get_view_image)

        self.remove_cmnt_status_btn = QtWidgets.QPushButton("Remove comment and status")
        self.review_main_layout_head.addWidget(self.remove_cmnt_status_btn)

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

        # signals
        self.current_shot_status.currentTextChanged.connect(self.setup_combo_status)
        self.current_shot_comment.textChanged.connect(self.comment_update)
        self.get_view_image.clicked.connect(self.get_gui_image)
        self.remove_cmnt_status_btn.clicked.connect(self.clean_cmnt_status)
        self.btn_note_prev.clicked.connect(self.annotate_prev)
        self.btn_note_next.clicked.connect(self.annotate_next)

        self.runme()


    def runme(self, arg1=None, arg2=None):
        self.rvWindow = rv.qtutils.sessionWindow()

        # Create DockWidget and add the Custom Widget to it
        self.dockWidget = QDockWidget("OpenPype Review", self.rvWindow)
        self.dockWidget.setWidget(self.customDockWidget)

        # Dock widget to the RV MainWindow
        self.rvWindow.addDockWidget(Qt.RightDockWidgetArea, self.dockWidget)
        self.setup_listeners()



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
        # new-source, graph-state-change, after-progressive-loading, media-relocated
        rv.commands.bind("default", "global", "source-media-set", self.graph_change, "Doc string")
        rv.commands.bind("default", "global", "after-graph-view-change", self.graph_change, "Doc string")


    def graph_change(self, event):
        print("image structure change")
        print(event.contents())
        print(rv.commands.sourcesAtFrame(rv.commands.frame()))
        print(rv.commands.frame())
        # update the view
        self.get_view_source()


    def get_view_source(self):
        self.current_loaded_viewnode = rv.commands.sourcesAtFrame(rv.commands.frame())[0]
        self.update_ui_attribs()


    def update_ui_attribs(self):
        node = self.current_loaded_viewnode
        # representation
        prop_representation = node + ".openpype.representation"
        prop_namespace = node + ".openpype.namespace"
        data_prop_namespace = rv.commands.getStringProperty(prop_namespace)[0]
        data_prop_representation_id = rv.commands.getStringProperty(prop_representation)[0]
        print("data_prop_namespace", data_prop_namespace)
        self.current_loaded_shot.setText(data_prop_namespace)
        self.setup_properties()
        self.get_comment()



    def setup_combo_status(self):
        # setup properties
        node = self.current_loaded_viewnode
        print(rv.commands.properties(node))
        att_prop = node + ".openpype_review.task_status"
        status = self.current_shot_status.currentText()
        rv.commands.setStringProperty(att_prop, [str(status)], True)
        self.current_shot_status.setCurrentText(status)


    def setup_properties(self):
        # setup properties
        node = self.current_loaded_viewnode
        print(rv.commands.properties(node))
        att_prop = node + ".openpype_review.task_status"

        if not rv.commands.propertyExists(att_prop):
            status = "In Review"
            rv.commands.newProperty(att_prop, rv.commands.StringType, 1)
            rv.commands.setStringProperty(att_prop, [str(status)], True)
            self.current_shot_status.setCurrentIndex(0)
        else:
            status = rv.commands.getStringProperty(att_prop)[0]
            self.current_shot_status.setCurrentText(status)


    def comment_update(self):
        node = self.current_loaded_viewnode
        comment = self.current_shot_comment.toPlainText()
        att_prop = node + ".openpype_review.task_comment"
        rv.commands.newProperty(att_prop, rv.commands.StringType, 1)
        rv.commands.setStringProperty(att_prop, [str(comment)], True)


    def get_comment(self):
        node = self.current_loaded_viewnode
        att_prop = node + ".openpype_review.task_comment"
        if not rv.commands.propertyExists(att_prop):
            rv.commands.newProperty(att_prop, rv.commands.StringType, 1)
            rv.commands.setStringProperty(att_prop, [""], True)
        else:
            status = rv.commands.getStringProperty(att_prop)[0]
            self.current_shot_comment.setPlainText(status)


    def clean_cmnt_status(self):
        attribs = []
        node = self.current_loaded_viewnode
        att_prop_cmnt = node + ".openpype_review.task_comment"
        att_prop_status = node + ".openpype_review.task_status"
        attribs.append(att_prop_cmnt)
        attribs.append(att_prop_status)

        for prop in attribs:
            if not rv.commands.propertyExists(prop):
                rv.commands.newProperty(prop, rv.commands.StringType, 1)
            rv.commands.setStringProperty(prop, [""], True)

        self.current_shot_status.setCurrentText("In Review")
        self.current_shot_comment.setPlainText("")


    def get_gui_image(self, filename=None):
        data = rv.commands.exportCurrentFrame("c:/temp/jpg.jpg")
        print(data)
        print("File saved")



    def annotate_next(self):
        all_notes = self.get_annotated_for_view()
        nxt = self.get_cycle_frame(frame=rv.commands.frame(), frames_in=all_notes, do="next")
        rv.commands.setFrame(int(nxt))
        rv.commands.redraw()


    def annotate_prev(self):
        all_notes = self.get_annotated_for_view()
        previous = self.get_cycle_frame(frame=rv.commands.frame(), frames_in=all_notes, do="prev")
        rv.commands.setFrame(int(previous))
        rv.commands.redraw()


    def get_annotated_for_view(self):
        annotated_frames = rv.extra_commands.findAnnotatedFrames()
        return annotated_frames


    def get_cycle_frame(self, frame=None, frames_in=None, do="next"):
        set_start = -1

        if len(frames_in) == 0:
            pass

        elif len(frames_in) == 1:
            for i,findframe in enumerate(frames_in):
                if frame == findframe:
                    return frame

        else:
            for i,findframe in enumerate(frames_in):
                if frame == findframe:
                    frames_in.remove(frame)
                    set_start = i

            if set_start != -1:
                if do == "next":
                    try:
                        data = [x for x in frames_in]
                        return data[set_start]
                    except:
                        return data[0]
                else:
                    for y,num in enumerate(frames_in, start=set_start):
                        return num
            else:
                if do == "next":
                    next_frame = min([i for i in frames_in if frame < i])
                    return next_frame
                else:
                    prev_frame = max([i for i in frames_in if frame > i])
                    return prev_frame



    def echo_change_update(self):
        print("CHANGE")

        print(self.current_loaded_viewnode)
        node = self.current_loaded_viewnode
        #print(node)
        print(rv.commands.properties(node))
        # representation
        prop_representation = node + ".openpype.representation"
        prop_namespace = node + ".openpype.namespace"
        data_prop_namespace = rv.commands.getStringProperty(prop_namespace)[0]
        data_prop_representation_id = rv.commands.getStringProperty(prop_representation)[0]
        print("data_prop_namespace", data_prop_namespace)
        print("data_prop_representation_id", data_prop_representation_id)
        from openpype.client import get_representations, get_representation_parents
        project_name = os.environ["AVALON_PROJECT"]
        representations = get_representations(project_name,
                                           representation_ids=[data_prop_representation_id])
        print("REPR")
        for rep in representations:
            print(rep)
        info = rv.extra_commands.sourceMetaInfoAtFrame(rv.commands.frame())
        print("info", info)


    def get_task_status(self):
        import ftrack_api
        session = ftrack_api.Session(auto_connect_event_hub=False)
        self.log.debug("Ftrack user: \"{0}\"".format(session.api_user))
        project_name = legacy_io.Session["AVALON_PROJECT"]
        project_entity = session.query((
            "select project_schema from Project where full_name is \"{}\""
        ).format(project_name)).one()
        project_schema = project_entity["project_schema"]



def createMode():
    return ReviewMenu()