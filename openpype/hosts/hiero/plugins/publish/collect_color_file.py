import re
import os.path
import hiero
import pyblish.api
from glob import glob
from datetime import datetime
from qtpy import QtWidgets, QtCore, QtGui

##################
# TODO: Determine if there is only one color file for shot or multiple color file for multiuple plates
##################

COLOR_FILE_EXTS = ("ccc", "cc", "cdl", "edl")

def parse_edl_events(path, color_edits_only=False):
    with open(path, "r") as f:
        edl_data = f.read()

    # Define regex patterns
    edit_pattern = r"(?<=[\n\r])(?P<edit>\d+\s+[\s\S]*?)(?=([\n\r]+\d+)|\Z)"
    sop_pattern = r"[*]\s?ASC[_]SOP\s+[(]\s?(?P<sR>[-]?\d+[.]\d{4,6})\s+(?P<sG>[-]?\d+[.]\d{4,6})\s+(?P<sB>[-]?\d+[.]\d{4,6})\s?[)]\s?[(]\s?(?P<oR>[-]?\d+[.]\d{4,6})\s+(?P<oG>[-]?\d+[.]\d{4,6})\s+(?P<oB>[-]?\d+[.]\d{4,6})\s?[)]\s?[(]\s?(?P<pR>[-]?\d+[.]\d{4,6})\s+(?P<pG>[-]?\d+[.]\d{4,6})\s+(?P<pB>[-]?\d+[.]\d{4,6})\s?[)]\s?"
    sat_pattern = r"[*]\s?ASC_SAT\s+(?P<sat>\d+[.]*\d*)"
    tape_pattern = r"\d+\s*(?P<source>[\S]*)(?=\s*)"
    clip_name_pattern = r"[*]\s?FROM[ ]*CLIP[ ]*NAME:\s*(?P<clip_name>.+)"
    loc_pattern = r"[*]\s?LOC:\s?.+\b(?<!_)(?P<LOC>[\w]{3,4}_((?<=_)[\w]{3,4}_){1,2}[\w]{3,4}(?<!_)(_[\w]{1,}){0,})\b"

    # Need to find first entry in edit list for range
    first_match = re.search(edit_pattern, edl_data)
    first_entry = int(first_match.group().split(" ", 1)[0]) if first_match else 1

    edl = {"events": {}}
    for edit_match in re.finditer(edit_pattern, edl_data):
        slope, offset, power, sat = None, None, None, None

        edit_value = edit_match.group("edit")
        # Determine if color data is present in event and store it
        sop_match = re.search(sop_pattern, edit_value)
        if sop_match:
            slope, offset, power = (
                tuple(map(float, (sop_match.group("sR"), sop_match.group("sG"), sop_match.group("sB")))),
                tuple(map(float, (sop_match.group("oR"), sop_match.group("oG"), sop_match.group("oB")))),
                tuple(map(float, (sop_match.group("pR"), sop_match.group("pG"), sop_match.group("pB")))),
            )

        # Always record even numbers
        entry = str(int(edit_value.split(" ", 1)[0]))
        # edl["entries"].append(entry)

        # Clip Name value
        clip_name_match = re.search(clip_name_pattern, edit_value)
        clip_name_value = clip_name_match.group("clip_name") if clip_name_match else ""

        # Tape value
        tape_match = re.search(tape_pattern, edit_value)
        tape_value = tape_match.group("source") if tape_match else ""

        # LOC value
        loc_match = re.search(loc_pattern, edit_value)
        loc_value = loc_match.group("LOC") if loc_match else ""


        # Do rest of regex find if color data was found.
        if not (slope is None and offset is None and power is None):
            # Sat value doesn't need to be found. If not found default to 1
            sat_match = re.search(sat_pattern, edit_value)
            sat = sat_match.group("sat") if sat_match else 1

            edl["events"][entry] = {
                "tape": tape_value,
                "clip_name": clip_name_value,
                "LOC": loc_value,
                "slope": slope,
                 "offset": offset,
                 "power": power,
                 "sat": sat,
                 }
        else:
            if not color_edits_only:
                edl["events"][entry] = {
                    "tape": tape_value,
                    "clip_name": clip_name_value,
                    "LOC": loc_value,
                }

    # Add last found entry from edit list iteration
    last_entry = int(edit_value.split(" ", 1)[0])

    # Finish EDL info
    edl["first_entry"] = first_entry
    edl["last_entry"] = last_entry

    return edl


def parse_cdl(path):
    with open(path, "r") as f:
        cdl_data = f.read().lower()

    cdl = {}

    slope_pattern = r"<slope>(?P<sR>[-,\d,.]*)[ ]{1}(?P<sG>[-,\d,.]+)[ ]{1}(?P<sB>[-,\d,.]*)</slope>"
    offset_pattern = r"<offset>(?P<oR>[-,\d,.]*)[ ]{1}(?P<oG>[-,\d,.]+)[ ]{1}(?P<oB>[-,\d,.]*)</offset>"
    power_pattern = r"<power>(?P<pR>[-,\d,.]*)[ ]{1}(?P<pG>[-,\d,.]+)[ ]{1}(?P<pB>[-,\d,.]*)</power>"
    sat_pattern = r"<saturation\>(?P<sat>[-,\d,.]+)</saturation\>"
    path_pattern = r"<originalpath\>(?P<path>.*)<\/originalpath\>"

    slope_match = re.search(slope_pattern, cdl_data)
    if slope_match:
        slope = (tuple(map(float, (slope_match.group("sR"), slope_match.group("sG"), slope_match.group("sB")))))
        cdl["slope"] = slope

    offset_match = re.search(offset_pattern, cdl_data)
    if offset_match:
        offset = (tuple(map(float, (offset_match.group("oR"), offset_match.group("oG"), offset_match.group("oB")))))
        cdl["offset"] = offset

    power_match = re.search(power_pattern, cdl_data)
    if power_match:
        power = (tuple(map(float, (power_match.group("pR"), power_match.group("pG"), power_match.group("pB")))))
        cdl["power"] = power

    sat_match = re.search(sat_pattern, cdl_data)
    if sat_match:
        sat = float(sat_match.group("sat"))
        cdl["sat"] = sat

    path_match = re.search(path_pattern, cdl_data)
    if path_match:
        path_value = path_match.group("path")
        cdl["file"] = path_value

    return cdl


class MissingColorFile(QtWidgets.QDialog):
    """
    What happens if CCC is found and has more than one ID. Need the ability to select the ID
    """
    data = {}
    default_browser_path = ""
    prev_file_path_input = ""
    prev_edl_entries_path = ""
    edl = {}

    def __init__(self, shot_name, source_name, main_grade, parent=None):
        super(MissingColorFile, self).__init__(parent)
        self.shot_name = shot_name
        self.source_name = source_name
        self.main_grade = main_grade

        self.setWindowTitle("Locate Color File")
        width = 519
        height = 386
        self.setFixedSize(width, height)

        # Fonts
        header_font = QtGui.QFont()
        header_font.setPointSize(20)

        # All layouts are added to widgets. This allows all content to be added as widgets
        self.content_widget = [QtWidgets.QWidget(self)]

        # Info Layout
        info_widget = QtWidgets.QWidget(self)
        info_layout = QtWidgets.QVBoxLayout(info_widget)
        info_msg_1 = "Grade not located!"
        self.information_label_1 = QtWidgets.QLabel(info_msg_1)
        self.information_label_1.setFont(header_font)
        info_layout.addWidget(self.information_label_1)
        info_layout.setAlignment(self.information_label_1, QtCore.Qt.AlignCenter)
        info_msg_2 = """Shot: {0}\nPlate: {1}\n\nPlease locate Grade File and determine if it's the shot Main Grade""".format(
            self.shot_name, self.source_name)
        self.information_label_2 = QtWidgets.QLabel(info_msg_2)
        info_layout.addWidget(self.information_label_2)
        self.content_widget.append(info_widget)

        # Input Layout
        input_widget = QtWidgets.QWidget(self)
        input_layout = QtWidgets.QGridLayout(input_widget)
        self.file_path_label = QtWidgets.QLabel("Grade Path:")
        self.file_path_input = QtWidgets.QLineEdit("")
        self.file_path_browse = QtWidgets.QPushButton("")

        file_browse_pixmap = QtWidgets.QStyle.SP_DialogOpenButton
        file_browse_icon = self.style().standardIcon(file_browse_pixmap)
        self.file_path_browse.setIcon(file_browse_icon)

        self.file_path_browse.setMaximumWidth(22)
        self.main_grade_checkbox = QtWidgets.QCheckBox("Main Grade")
        self.main_grade_checkbox.setChecked(self.main_grade)
        input_layout.addWidget(self.file_path_label, 0, 0)
        input_layout.addWidget(self.file_path_input, 0, 1)
        input_layout.addWidget(self.file_path_browse, 0, 2)
        input_layout.addWidget(self.main_grade_checkbox, 1, 1)
        self.content_widget.append(input_widget)

        # Layout for EDL and SOPS
        info_display_widget = QtWidgets.QWidget(self)
        info_display_layout = QtWidgets.QHBoxLayout(info_display_widget)

        # EDL Layout
        self.edl_widget = QtWidgets.QWidget(self)
        self.edl_widget.setStyleSheet("background-color: rgb(43, 43, 43)")
        self.edl_widget.hide()
        edl_layout = QtWidgets.QGridLayout(self.edl_widget)
        # EDL event-viewing
        event_and_view = QtWidgets.QHBoxLayout()
        self.entry_label = QtWidgets.QLabel("Event #:")
        self.entry_number = QtWidgets.QSpinBox()
        self.open_file = QtWidgets.QPushButton("Open EDL")
        self.open_file.setStyleSheet("background-color: rgb(55, 55, 55)")
        self.open_file.setMinimumWidth(70)
        self.open_file.setMaximumWidth(70)
        event_and_view.addWidget(self.entry_number)
        event_and_view.addWidget(self.open_file)
        self.entry_number.setMinimumWidth(55)
        self.entry_number.setMaximumWidth(55)
        self.entry_number.setMinimumHeight(20)
        self.entry_number.setMaximumHeight(20)
        self.tape_label = QtWidgets.QLabel("Tape Name:")
        self.tape_name = QtWidgets.QLineEdit()
        self.tape_name.setReadOnly(True)
        self.tape_name.setMinimumWidth(149)
        self.tape_name.setMaximumWidth(149)
        self.clip_name_label = QtWidgets.QLabel("Clip Name:")
        self.clip_name = QtWidgets.QLineEdit()
        self.clip_name.setReadOnly(True)
        self.clip_name.setMinimumWidth(149)
        self.clip_name.setMaximumWidth(149)
        self.loc_name_label = QtWidgets.QLabel("LOC {shot}:")
        self.loc_name = QtWidgets.QLineEdit()
        self.loc_name.setReadOnly(True)
        self.loc_name.setMinimumWidth(149)
        self.loc_name.setMaximumWidth(149)
        edl_layout.addWidget(self.entry_label, 0, 0)
        edl_layout.addLayout(event_and_view, 0, 1)
        edl_layout.addWidget(self.tape_label, 1, 0)
        edl_layout.addWidget(self.tape_name, 1, 1)
        edl_layout.addWidget(self.clip_name_label, 2, 0)
        edl_layout.addWidget(self.clip_name, 2, 1)
        edl_layout.addWidget(self.loc_name_label, 3, 0)
        edl_layout.addWidget(self.loc_name, 3, 1)

        # SOPS Layout
        sops_widget = QtWidgets.QWidget(self)
        sops_widget.setStyleSheet("background-color: rgb(43, 43, 43)")
        sops_layout = QtWidgets.QGridLayout(sops_widget)

        slope_layout = QtWidgets.QHBoxLayout()
        offset_layout = QtWidgets.QHBoxLayout()
        power_layout = QtWidgets.QHBoxLayout()
        sat_layout = QtWidgets.QHBoxLayout()
        self.slope_label = QtWidgets.QLabel("Slope:")
        self.slope_r_input = QtWidgets.QLineEdit("NA")
        self.slope_r_input.setReadOnly(True)
        self.slope_r_input.setMinimumWidth(50)
        self.slope_r_input.setMaximumWidth(50)
        self.slope_g_input = QtWidgets.QLineEdit("NA")
        self.slope_g_input.setReadOnly(True)
        self.slope_g_input.setMinimumWidth(50)
        self.slope_g_input.setMaximumWidth(50)
        self.slope_b_input = QtWidgets.QLineEdit("NA")
        self.slope_b_input.setReadOnly(True)
        self.slope_b_input.setMinimumWidth(50)
        self.slope_b_input.setMaximumWidth(50)
        self.offset_label = QtWidgets.QLabel("Offset:")
        self.offset_r_input = QtWidgets.QLineEdit("NA")
        self.offset_r_input.setReadOnly(True)
        self.offset_r_input.setMinimumWidth(50)
        self.offset_r_input.setMaximumWidth(50)
        self.offset_g_input = QtWidgets.QLineEdit("NA")
        self.offset_g_input.setReadOnly(True)
        self.offset_g_input.setMinimumWidth(50)
        self.offset_g_input.setMaximumWidth(50)
        self.offset_b_input = QtWidgets.QLineEdit("NA")
        self.offset_b_input.setReadOnly(True)
        self.offset_b_input.setMinimumWidth(50)
        self.offset_b_input.setMaximumWidth(50)
        self.power_label = QtWidgets.QLabel("Power:")
        self.power_r_input = QtWidgets.QLineEdit("NA")
        self.power_r_input.setReadOnly(True)
        self.power_r_input.setMinimumWidth(50)
        self.power_r_input.setMaximumWidth(50)
        self.power_g_input = QtWidgets.QLineEdit("NA")
        self.power_g_input.setReadOnly(True)
        self.power_g_input.setMinimumWidth(50)
        self.power_g_input.setMaximumWidth(50)
        self.power_b_input = QtWidgets.QLineEdit("NA")
        self.power_b_input.setReadOnly(True)
        self.power_b_input.setMinimumWidth(50)
        self.power_b_input.setMaximumWidth(50)
        self.sat_label = QtWidgets.QLabel("Sat:")
        self.sat_input = QtWidgets.QLineEdit("NA")
        self.sat_input.setReadOnly(True)
        self.sat_input.setMinimumWidth(42)
        self.sat_input.setMaximumWidth(42)
        slope_layout.addWidget(self.slope_r_input)
        slope_layout.addWidget(self.slope_g_input)
        slope_layout.addWidget(self.slope_b_input)
        offset_layout.addWidget(self.offset_r_input)
        offset_layout.addWidget(self.offset_g_input)
        offset_layout.addWidget(self.offset_b_input)
        power_layout.addWidget(self.power_r_input)
        power_layout.addWidget(self.power_g_input)
        power_layout.addWidget(self.power_b_input)
        sat_layout.addWidget(self.sat_input)

        sops_layout.addWidget(self.slope_label, 0, 0)
        sops_layout.addLayout(slope_layout, 0, 1)
        sops_layout.addWidget(self.offset_label, 1, 0)
        sops_layout.addLayout(offset_layout, 1, 1)
        sops_layout.addWidget(self.power_label, 2, 0)
        sops_layout.addLayout(power_layout, 2, 1)
        sops_layout.addWidget(self.sat_label, 3, 0)
        sops_layout.addLayout(sat_layout, 3, 1)

        info_h_spacer_item_1 = QtWidgets.QSpacerItem(10, 8, QtWidgets.QSizePolicy.Expanding,
                                                     QtWidgets.QSizePolicy.Fixed)
        info_display_layout.addItem(info_h_spacer_item_1)
        info_display_layout.addWidget(self.edl_widget)
        self.edl_sops_seperator = QtWidgets.QFrame()
        self.edl_sops_seperator.setFrameShape(QtWidgets.QFrame.VLine)
        self.edl_sops_seperator.setFrameShadow(QtWidgets.QFrame.Sunken)
        self.edl_sops_seperator.setSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        self.edl_sops_seperator.hide()
        info_display_layout.addWidget(self.edl_sops_seperator)
        info_display_layout.addWidget(sops_widget)
        info_h_spacer_item_3 = QtWidgets.QSpacerItem(10, 8, QtWidgets.QSizePolicy.Expanding,
                                                     QtWidgets.QSizePolicy.Fixed)
        info_display_layout.addItem(info_h_spacer_item_3)
        self.content_widget.append(info_display_widget)

        # Buttons Layout
        buttons_widget = QtWidgets.QWidget(self)
        buttons_layout = QtWidgets.QHBoxLayout(buttons_widget)
        buttons_h_spacer_item_1 = QtWidgets.QSpacerItem(10, 8, QtWidgets.QSizePolicy.Expanding,
                                                        QtWidgets.QSizePolicy.Fixed)
        self.blank_grade_button = QtWidgets.QPushButton("Blank Grade")
        buttons_h_spacer_item_2 = QtWidgets.QSpacerItem(10, 8, QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        self.accept_button = QtWidgets.QPushButton("Accept")
        self.cancel_button = QtWidgets.QPushButton("Cancel")
        buttons_layout.addItem(buttons_h_spacer_item_1)
        buttons_layout.addWidget(self.blank_grade_button)
        buttons_layout.addItem(buttons_h_spacer_item_2)
        buttons_layout.addWidget(self.accept_button)
        buttons_layout.addWidget(self.cancel_button)
        self.content_widget.append(buttons_widget)

        # Main layout of the dialog
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(0)

        # adding content widget
        for w in self.content_widget:
            main_layout.addWidget(w)

        # Connections
        self.file_path_browse.pressed.connect(self.open_color_file_browser)
        self.blank_grade_button.pressed.connect(self.blank_grade)
        self.accept_button.pressed.connect(self.check_and_accept)
        self.cancel_button.pressed.connect(self.cancel)
        self.file_path_input.textChanged.connect(self.set_sops_and_edl)
        self.entry_number.valueChanged.connect(self.set_edl_info)
        self.open_file.pressed.connect(self.open_text_file)

    def set_edl_entry_widgets(self):
        color_file_path = self.file_path_input.text()
        if self.prev_file_path_input == color_file_path:
            return

        is_edl = False
        if color_file_path.lower().endswith(".edl"):
            is_edl = True

        if os.path.isfile(color_file_path) and is_edl:
            self.edl_widget.show()
            self.edl_sops_seperator.show()

            edl = parse_edl_events(color_file_path)
            self.edl = edl
            self.entry_number.setMinimum(edl["first_entry"])
            self.entry_number.setMaximum(edl["last_entry"])

        else:
            self.edl_widget.hide()
            self.edl_sops_seperator.hide()

        self.prev_file_path_input = color_file_path

    def set_edl_info(self):
        event_number = self.entry_number.value()
        if self.edl:
            event_info = self.edl["events"][str(event_number)]
            self.tape_name.setText(event_info["tape"])
            self.clip_name.setText(event_info["clip_name"])
            self.loc_name.setText(event_info["LOC"])
            if event_info.get("slope"):
                self.set_sops_widgets(
                    event_info.get("slope"),
                    event_info.get("offset"),
                    event_info.get("power"),
                    event_info.get("sat")
                )

            else:
                self.set_sops_widgets(None, None, None, None)
        else:
            return

    def set_sops_from_cdl(self):
        """
        Driven by connection. Based on the change of file path.
        """
        file_path = self.file_path_input.text()
        file_extention = file_path.lower().rsplit(".", 1)[-1]
        if file_extention in ["ccc", "cc", "cdl"] and os.path.isfile(file_path):
            cdl = parse_cdl(file_path)
            self.set_sops_widgets(
                cdl.get("slope"),
                cdl.get("offset"),
                cdl.get("power"),
                cdl.get("sat")
            )
        else:
            return

    def set_sops_and_edl(self):
        file_path = self.file_path_input.text()
        file_extention = file_path.lower().rsplit(".", 1)[-1]

        if file_extention == "edl":
            self.edl_widget.show()
            self.edl_sops_seperator.show()
        else:
            self.edl_widget.hide()
            self.edl_sops_seperator.hide()

        color_file_path = file_path
        if self.prev_file_path_input == color_file_path:
            return

        if file_extention == "edl":
            self.set_edl_info()

            edl = parse_edl_events(color_file_path)
            self.edl = edl
            self.entry_number.setMinimum(edl["first_entry"])
            self.entry_number.setMaximum(edl["last_entry"])

        if file_extention in ["ccc", "cc", "cdl"] and os.path.isfile(file_path):
            cdl = parse_cdl(file_path)
            self.set_sops_widgets(
                cdl.get("slope"),
                cdl.get("offset"),
                cdl.get("power"),
                cdl.get("sat")
                )

        if not (file_extention in ["ccc", "cc", "cdl", "edl"] and os.path.isfile(file_path)):
            self.set_sops_widgets(None, None, None, None)
        else:
            self.prev_file_path_input = color_file_path

            return

    def set_sops_widgets(self, slope, offset, power, sat):
        if not slope:
            slope = ("NA", "NA", "NA")
        if not offset:
            offset = ("NA", "NA", "NA")
        if not power:
            power = ("NA", "NA", "NA")
        if sat is None:
            sat = "NA"

        # Set slope
        self.slope_r_input.setText(str(slope[0]))
        self.slope_g_input.setText(str(slope[1]))
        self.slope_b_input.setText(str(slope[2]))

        # Set Offset
        self.offset_r_input.setText(str(offset[0]))
        self.offset_g_input.setText(str(offset[1]))
        self.offset_b_input.setText(str(offset[2]))

        # Set Power
        self.power_r_input.setText(str(power[0]))
        self.power_g_input.setText(str(power[1]))
        self.power_b_input.setText(str(power[2]))

        # Set Saturation
        self.sat_input.setText(str(sat))

    def open_color_file_browser(self):
        # hiero.menu browse
        path_result = hiero.ui.openFileBrowser(caption="Color path", mode=1, initialPath=self.default_browser_path,
                                               multipleSelection=False)
        if path_result:
            if path_result[0].replace("\\", "/").endswith("/"):
                path_result = path_result[0][:-1]
            else:
                path_result = path_result[0]
            folder_path = path_result
        else:
            return

        self.file_path_input.setText(folder_path)

    def blank_grade(self):
        cdl = {
            "slope": (1, 1, 1),
            "offset": (1, 1, 1),
            "power": (1, 1, 1),
            "sat": 1
        }
        self.data["cdl"] = cdl

        self.accept()

    def open_text_file(self):
        path = self.file_path_input.text()
        if os.path.isfile(path):
            os.system("code {}".format(path))
        else:
            QtWidgets.QMessageBox.information(hiero.ui.mainWindow(),
                                              "Info", "Can't open file as it doesn't exist on disk")

    def set_data(self):
        cdl = {
            "slope": (self.slope_r_input.text(), self.slope_g_input.text(), self.slope_b_input.text()),
            "offset": (self.offset_r_input.text(), self.offset_g_input.text(), self.offset_b_input.text()),
            "power": (self.power_r_input.text(), self.power_g_input.text(), self.power_b_input.text()),
            "sat": self.sat_input.text()
        }
        data = {
            "path": self.file_path_input.text(),
            "event": self.entry_number.value(),
            "type": self.file_path_input.text().rsplit(".", 1)[-1],
            "cdl" : cdl
        }
        self.data = data

    def check_and_accept(self):
        # Test whether or not the new file path gives the proper result and if not then warn user
        color_file_path = self.file_path_input.text()
        color_file_path_ext = color_file_path.rsplit(".", 1)[-1]

        if not os.path.isfile(color_file_path):
            # Make sure that color file is a file on disk
            QtWidgets.QMessageBox.information(hiero.ui.mainWindow(), "Info",
                                              "Please make sure the file you selected exists")  # 3DL, Cube
            return

        if not color_file_path_ext in COLOR_FILE_EXTS:
            # Make sure that color file is correct
            QtWidgets.QMessageBox.information(hiero.ui.mainWindow(), "Info",
                                              "Please make sure the file you selected is a color file type\n\n'EDL, CCC, CC, CDL'")  # 3DL, Cube
            return

        self.set_data()
        if self.data["cdl"]["slope"][0] == "NA":
            QtWidgets.QMessageBox.information(hiero.ui.mainWindow(), "Info",
                                              "No color data found!\n\nIf this shot needs a blank grade press 'Blank Grade'")  # 3DL, Cube
            return

        self.accept()

    def cancel(self):
        self.data = {}

        self.close()


def get_files(package_path, filters):
    depth = "/*"
    files = {key:[] for key in filters}
    more_folders = True
    while True and more_folders:
        more_folders = False
        for item in glob(package_path + depth):
            if os.path.isdir(item):
                more_folders = True
            else:
                file_ext = item.rsplit(".")[-1].lower()
                if file_ext in filters:
                    files[file_ext].append(item)
        depth += "/*"

    return files


def priority_color_file(color_files, item_name, source_name):
    """Priority is given to the closest match of source_name then item_name as well as found file type"""
    matches = []
    for color_ext in COLOR_FILE_EXTS:
        ext_color_files = color_files.get(color_ext)
        if ext_color_files:
            for color_file in ext_color_files:
                # Check non edls first. Sometimes edls don't carry ground truth SOPS
                if not color_ext == "edl":
                    # Name match priority
                    priority = None
                    color_file_name = os.path.basename(color_file)
                    if source_name == color_file_name:
                        priority = 0
                    elif source_name in color_file_name:
                        priority = 4
                    elif item_name == color_file_name:
                        priority = 8
                    elif item_name in color_file_name:
                        priority = 12

                    if not priority is None:
                        # Distinguish type priority
                        if color_ext == "cc":
                            priority += 0
                        elif color_ext == "ccc":
                            priority += 1
                        # EDL is priority += 2
                        elif color_ext == "cdl":
                            priority += 3

                        cdl = parse_cdl(color_file)
                        matches.append((priority, cdl, color_file))
                else:
                    edits = parse_edl_events(color_file, color_edits_only=True)
                    for edit in edits["events"]:
                        edl_event = edits["events"][edit]
                        print(edl_event, "edl_event")
                        cdl = {
                            "slope": edl_event["slope"],
                            "offset": edl_event["offset"],
                            "power": edl_event["power"],
                        }
                        loc_name = edl_event["LOC"]
                        if source_name == loc_name:
                            matches.append((2, cdl, color_file))
                        elif source_name in loc_name:
                            matches.append((6, cdl, color_file))
                        elif item_name == loc_name:
                            matches.append((10, cdl, color_file))
                        elif item_name in loc_name:
                            matches.append((14, cdl, color_file))

    if matches:
        return sorted(matches, key=lambda x: x[0])[0]
    else:
        return None


def get_color_file(source_path, item_name, source_name):
    """Find best guess color file for a given source path"""
    package_path_end = re.split("/incoming/\d+/", source_path)[1]
    package_path = "{0}{1}".format(
        source_path.split(package_path_end.split("/")[0])[0],
        package_path_end.split("/")[0]
    )

    incoming_path = os.path.dirname(source_path.split("/" + package_path_end.split("/")[0])[0])
    incoming_packages = [d for d in sorted(glob(incoming_path + "/*")) if os.path.isdir(d)]
    # Create Package list
    sorted_incoming = [package_path] + sorted(
        incoming_packages,
        key=lambda x: int(os.path.basename(x)) if os.path.basename(x).isdigit() else int(
            datetime.fromtimestamp(os.path.getctime(x)).strftime("%Y%m%d"))
    )

    color_file = None, None, None
    for path in sorted_incoming:
        color_files = get_files(path, COLOR_FILE_EXTS)

        # Prioritize which color files will be used
        color_file = priority_color_file(color_files, item_name, source_name)
        if color_file:
            break

    return color_file


class CollectColorFile(pyblish.api.InstancePlugin):
    """Collect Color File for plate."""

    order = pyblish.api.CollectorOrder
    label = "Collect Color File"
    families = ["plate"]

    def process(self, instance):
        track_item = instance.data["item"]
        item_name = track_item.name()
        source_name = track_item.source().name()
        source_path = track_item.source().mediaSource().firstpath()
        main_grade = False
        cdl = None
        color_file = ""

        # TODO: Check to make sure that the source_path is in incoming
        incoming_pattern = r"\/proj\/.*\/incoming"
        incoming_match = re.match(incoming_pattern, source_path)
        if incoming_match:
            priority, cdl, color_file = get_color_file(source_path, item_name, source_name)

        if not color_file:
            dialog = MissingColorFile(item_name, source_name, main_grade)
            dialog_result = dialog.exec()
            print(dialog.data, "dialog_result.data")
            if dialog_result:
                cdl = dialog.data["cdl"]
                color_file = dialog.data["path"]

        cdl["file"] = color_file

        if cdl:
            instance.data["cdl"] = cdl
            self.log.info("Collected CDL: {0}".format(cdl))
        else:
           self.log.critical("No color file found for plate '{0}'-'{1}'".format(item_name, source_name))
