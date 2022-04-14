import os
import re
import shutil
from copy import deepcopy
from xml.etree import ElementTree as ET

from Qt import QtCore, QtWidgets

import openpype.api as openpype
import qargparse
from openpype import style
from openpype.pipeline import LegacyCreator, LoaderPlugin

from . import constants
from . import lib as flib
from . import pipeline as fpipeline

log = openpype.Logger.get_logger(__name__)


class CreatorWidget(QtWidgets.QDialog):

    # output items
    items = dict()
    _results_back = None

    def __init__(self, name, info, ui_inputs, parent=None):
        super(CreatorWidget, self).__init__(parent)

        self.setObjectName(name)

        self.setWindowFlags(
            QtCore.Qt.Window
            | QtCore.Qt.CustomizeWindowHint
            | QtCore.Qt.WindowTitleHint
            | QtCore.Qt.WindowCloseButtonHint
            | QtCore.Qt.WindowStaysOnTopHint
        )
        self.setWindowTitle(name or "Pype Creator Input")
        self.resize(500, 700)

        # Where inputs and labels are set
        self.content_widget = [QtWidgets.QWidget(self)]
        top_layout = QtWidgets.QFormLayout(self.content_widget[0])
        top_layout.setObjectName("ContentLayout")
        top_layout.addWidget(Spacer(5, self))

        # first add widget tag line
        top_layout.addWidget(QtWidgets.QLabel(info))

        # main dynamic layout
        self.scroll_area = QtWidgets.QScrollArea(self, widgetResizable=True)
        self.scroll_area.setVerticalScrollBarPolicy(
            QtCore.Qt.ScrollBarAsNeeded)
        self.scroll_area.setVerticalScrollBarPolicy(
            QtCore.Qt.ScrollBarAlwaysOn)
        self.scroll_area.setHorizontalScrollBarPolicy(
            QtCore.Qt.ScrollBarAlwaysOff)
        self.scroll_area.setWidgetResizable(True)

        self.content_widget.append(self.scroll_area)

        scroll_widget = QtWidgets.QWidget(self)
        in_scroll_area = QtWidgets.QVBoxLayout(scroll_widget)
        self.content_layout = [in_scroll_area]

        # add preset data into input widget layout
        self.items = self.populate_widgets(ui_inputs)
        self.scroll_area.setWidget(scroll_widget)

        # Confirmation buttons
        btns_widget = QtWidgets.QWidget(self)
        btns_layout = QtWidgets.QHBoxLayout(btns_widget)

        cancel_btn = QtWidgets.QPushButton("Cancel")
        btns_layout.addWidget(cancel_btn)

        ok_btn = QtWidgets.QPushButton("Ok")
        btns_layout.addWidget(ok_btn)

        # Main layout of the dialog
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(0)

        # adding content widget
        for w in self.content_widget:
            main_layout.addWidget(w)

        main_layout.addWidget(btns_widget)

        ok_btn.clicked.connect(self._on_ok_clicked)
        cancel_btn.clicked.connect(self._on_cancel_clicked)

        self.setStyleSheet(style.load_stylesheet())

    @classmethod
    def set_results_back(cls, value):
        cls._results_back = value

    @classmethod
    def get_results_back(cls):
        return cls._results_back

    def _on_ok_clicked(self):
        log.debug("ok is clicked: {}".format(self.items))
        results_back = self._values(self.items)
        self.set_results_back(results_back)
        self.close()

    def _on_cancel_clicked(self):
        self.set_results_back(None)
        self.close()

    def showEvent(self, event):
        self.set_results_back(None)
        super(CreatorWidget, self).showEvent(event)

    def _values(self, data, new_data=None):
        new_data = new_data or dict()
        for k, v in data.items():
            new_data[k] = {
                "target": None,
                "value": None
            }
            if v["type"] == "dict":
                new_data[k]["target"] = v["target"]
                new_data[k]["value"] = self._values(v["value"])
            if v["type"] == "section":
                new_data.pop(k)
                new_data = self._values(v["value"], new_data)
            elif getattr(v["value"], "currentText", None):
                new_data[k]["target"] = v["target"]
                new_data[k]["value"] = v["value"].currentText()
            elif getattr(v["value"], "isChecked", None):
                new_data[k]["target"] = v["target"]
                new_data[k]["value"] = v["value"].isChecked()
            elif getattr(v["value"], "value", None):
                new_data[k]["target"] = v["target"]
                new_data[k]["value"] = v["value"].value()
            elif getattr(v["value"], "text", None):
                new_data[k]["target"] = v["target"]
                new_data[k]["value"] = v["value"].text()

        return new_data

    def camel_case_split(self, text):
        matches = re.finditer(
            '.+?(?:(?<=[a-z])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])|$)', text)
        return " ".join([str(m.group(0)).capitalize() for m in matches])

    def create_row(self, layout, type_name, text, **kwargs):
        # get type attribute from qwidgets
        attr = getattr(QtWidgets, type_name)

        # convert label text to normal capitalized text with spaces
        label_text = self.camel_case_split(text)

        # assign the new text to lable widget
        label = QtWidgets.QLabel(label_text)
        label.setObjectName("LineLabel")

        # create attribute name text strip of spaces
        attr_name = text.replace(" ", "")

        # create attribute and assign default values
        setattr(
            self,
            attr_name,
            attr(parent=self))

        # assign the created attribute to variable
        item = getattr(self, attr_name)
        for func, val in kwargs.items():
            if getattr(item, func):
                func_attr = getattr(item, func)
                func_attr(val)

        # add to layout
        layout.addRow(label, item)

        return item

    def populate_widgets(self, data, content_layout=None):
        """
        Populate widget from input dict.

        Each plugin has its own set of widget rows defined in dictionary
        each row values should have following keys: `type`, `target`,
        `label`, `order`, `value` and optionally also `toolTip`.

        Args:
            data (dict): widget rows or organized groups defined
                         by types `dict` or `section`
            content_layout (QtWidgets.QFormLayout)[optional]: used when nesting

        Returns:
            dict: redefined data dict updated with created widgets

        """

        content_layout = content_layout or self.content_layout[-1]
        # fix order of process by defined order value
        ordered_keys = list(data.keys())
        for k, v in data.items():
            try:
                # try removing a key from index which should
                # be filled with new
                ordered_keys.pop(v["order"])
            except IndexError:
                pass
            # add key into correct order
            ordered_keys.insert(v["order"], k)

        # process ordered
        for k in ordered_keys:
            v = data[k]
            tool_tip = v.get("toolTip", "")
            if v["type"] == "dict":
                self.content_layout.append(QtWidgets.QWidget(self))
                content_layout.addWidget(self.content_layout[-1])
                self.content_layout[-1].setObjectName("sectionHeadline")

                headline = QtWidgets.QVBoxLayout(self.content_layout[-1])
                headline.addWidget(Spacer(20, self))
                headline.addWidget(QtWidgets.QLabel(v["label"]))

                # adding nested layout with label
                self.content_layout.append(QtWidgets.QWidget(self))
                self.content_layout[-1].setObjectName("sectionContent")

                nested_content_layout = QtWidgets.QFormLayout(
                    self.content_layout[-1])
                nested_content_layout.setObjectName("NestedContentLayout")
                content_layout.addWidget(self.content_layout[-1])

                # add nested key as label
                data[k]["value"] = self.populate_widgets(
                    v["value"], nested_content_layout)

            if v["type"] == "section":
                self.content_layout.append(QtWidgets.QWidget(self))
                content_layout.addWidget(self.content_layout[-1])
                self.content_layout[-1].setObjectName("sectionHeadline")

                headline = QtWidgets.QVBoxLayout(self.content_layout[-1])
                headline.addWidget(Spacer(20, self))
                headline.addWidget(QtWidgets.QLabel(v["label"]))

                # adding nested layout with label
                self.content_layout.append(QtWidgets.QWidget(self))
                self.content_layout[-1].setObjectName("sectionContent")

                nested_content_layout = QtWidgets.QFormLayout(
                    self.content_layout[-1])
                nested_content_layout.setObjectName("NestedContentLayout")
                content_layout.addWidget(self.content_layout[-1])

                # add nested key as label
                data[k]["value"] = self.populate_widgets(
                    v["value"], nested_content_layout)

            elif v["type"] == "QLineEdit":
                data[k]["value"] = self.create_row(
                    content_layout, "QLineEdit", v["label"],
                    setText=v["value"], setToolTip=tool_tip)
            elif v["type"] == "QComboBox":
                data[k]["value"] = self.create_row(
                    content_layout, "QComboBox", v["label"],
                    addItems=v["value"], setToolTip=tool_tip)
            elif v["type"] == "QCheckBox":
                data[k]["value"] = self.create_row(
                    content_layout, "QCheckBox", v["label"],
                    setChecked=v["value"], setToolTip=tool_tip)
            elif v["type"] == "QSpinBox":
                data[k]["value"] = self.create_row(
                    content_layout, "QSpinBox", v["label"],
                    setValue=v["value"], setMinimum=0,
                    setMaximum=100000, setToolTip=tool_tip)
        return data


class Spacer(QtWidgets.QWidget):
    def __init__(self, height, *args, **kwargs):
        super(self.__class__, self).__init__(*args, **kwargs)

        self.setFixedHeight(height)

        real_spacer = QtWidgets.QWidget(self)
        real_spacer.setObjectName("Spacer")
        real_spacer.setFixedHeight(height)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(real_spacer)

        self.setLayout(layout)


class Creator(LegacyCreator):
    """Creator class wrapper
    """
    clip_color = constants.COLOR_MAP["purple"]
    rename_index = None

    def __init__(self, *args, **kwargs):
        super(Creator, self).__init__(*args, **kwargs)
        self.presets = openpype.get_current_project_settings()[
            "flame"]["create"].get(self.__class__.__name__, {})

        # adding basic current context flame objects
        self.project = flib.get_current_project()
        self.sequence = flib.get_current_sequence(flib.CTX.selection)

        if (self.options or {}).get("useSelection"):
            self.selected = flib.get_sequence_segments(self.sequence, True)
        else:
            self.selected = flib.get_sequence_segments(self.sequence)

    def create_widget(self, *args, **kwargs):
        widget = CreatorWidget(*args, **kwargs)
        widget.exec_()
        return widget.get_results_back()


class PublishableClip:
    """
    Convert a segment to publishable instance

    Args:
        segment (flame.PySegment): flame api object
        kwargs (optional): additional data needed for rename=True (presets)

    Returns:
        flame.PySegment: flame api object
    """
    vertical_clip_match = {}
    marker_data = {}
    types = {
        "shot": "shot",
        "folder": "folder",
        "episode": "episode",
        "sequence": "sequence",
        "track": "sequence",
    }

    # parents search patern
    parents_search_patern = r"\{([a-z]*?)\}"

    # default templates for non-ui use
    rename_default = False
    hierarchy_default = "{_folder_}/{_sequence_}/{_track_}"
    clip_name_default = "shot_{_trackIndex_:0>3}_{_clipIndex_:0>4}"
    subset_name_default = "[ track name ]"
    review_track_default = "[ none ]"
    subset_family_default = "plate"
    count_from_default = 10
    count_steps_default = 10
    vertical_sync_default = False
    driving_layer_default = ""
    index_from_segment_default = False
    use_shot_name_default = False

    def __init__(self, segment, **kwargs):
        self.rename_index = kwargs["rename_index"]
        self.family = kwargs["family"]
        self.log = kwargs["log"]

        # get main parent objects
        self.current_segment = segment
        sequence_name = flib.get_current_sequence([segment]).name.get_value()
        self.sequence_name = str(sequence_name).replace(" ", "_")

        self.clip_data = flib.get_segment_attributes(segment)
        # segment (clip) main attributes
        self.cs_name = self.clip_data["segment_name"]
        self.cs_index = int(self.clip_data["segment"])
        self.shot_name = self.clip_data["shot_name"]

        # get track name and index
        self.track_index = int(self.clip_data["track"])
        track_name = self.clip_data["track_name"]
        self.track_name = str(track_name).replace(" ", "_").replace(
            "*", "noname{}".format(self.track_index))

        # adding tag.family into tag
        if kwargs.get("avalon"):
            self.marker_data.update(kwargs["avalon"])

        # add publish attribute to marker data
        self.marker_data.update({"publish": True})

        # adding ui inputs if any
        self.ui_inputs = kwargs.get("ui_inputs", {})

        self.log.info("Inside of plugin: {}".format(
            self.marker_data
        ))
        # populate default data before we get other attributes
        self._populate_segment_default_data()

        # use all populated default data to create all important attributes
        self._populate_attributes()

        # create parents with correct types
        self._create_parents()

    def convert(self):

        # solve segment data and add them to marker data
        self._convert_to_marker_data()

        # if track name is in review track name and also if driving track name
        # is not in review track name: skip tag creation
        if (self.track_name in self.review_layer) and (
                self.driving_layer not in self.review_layer):
            return

        # deal with clip name
        new_name = self.marker_data.pop("newClipName")

        if self.rename and not self.use_shot_name:
            # rename segment
            self.current_segment.name = str(new_name)
            self.marker_data["asset"] = str(new_name)
        elif self.use_shot_name:
            self.marker_data["asset"] = self.shot_name
            self.marker_data["hierarchyData"]["shot"] = self.shot_name
        else:
            self.marker_data["asset"] = self.cs_name
            self.marker_data["hierarchyData"]["shot"] = self.cs_name

        if self.marker_data["heroTrack"] and self.review_layer:
            self.marker_data["reviewTrack"] = self.review_layer
        else:
            self.marker_data["reviewTrack"] = None

        # create pype tag on track_item and add data
        fpipeline.imprint(self.current_segment, self.marker_data)

        return self.current_segment

    def _populate_segment_default_data(self):
        """ Populate default formating data from segment. """

        self.current_segment_default_data = {
            "_folder_": "shots",
            "_sequence_": self.sequence_name,
            "_track_": self.track_name,
            "_clip_": self.cs_name,
            "_trackIndex_": self.track_index,
            "_clipIndex_": self.cs_index
        }

    def _populate_attributes(self):
        """ Populate main object attributes. """
        # segment frame range and parent track name for vertical sync check
        self.clip_in = int(self.clip_data["record_in"])
        self.clip_out = int(self.clip_data["record_out"])

        # define ui inputs if non gui mode was used
        self.shot_num = self.cs_index
        self.log.debug(
            "____ self.shot_num: {}".format(self.shot_num))

        # ui_inputs data or default values if gui was not used
        self.rename = self.ui_inputs.get(
            "clipRename", {}).get("value") or self.rename_default
        self.use_shot_name = self.ui_inputs.get(
            "useShotName", {}).get("value") or self.use_shot_name_default
        self.clip_name = self.ui_inputs.get(
            "clipName", {}).get("value") or self.clip_name_default
        self.hierarchy = self.ui_inputs.get(
            "hierarchy", {}).get("value") or self.hierarchy_default
        self.hierarchy_data = self.ui_inputs.get(
            "hierarchyData", {}).get("value") or \
            self.current_segment_default_data.copy()
        self.index_from_segment = self.ui_inputs.get(
            "segmentIndex", {}).get("value") or self.index_from_segment_default
        self.count_from = self.ui_inputs.get(
            "countFrom", {}).get("value") or self.count_from_default
        self.count_steps = self.ui_inputs.get(
            "countSteps", {}).get("value") or self.count_steps_default
        self.subset_name = self.ui_inputs.get(
            "subsetName", {}).get("value") or self.subset_name_default
        self.subset_family = self.ui_inputs.get(
            "subsetFamily", {}).get("value") or self.subset_family_default
        self.vertical_sync = self.ui_inputs.get(
            "vSyncOn", {}).get("value") or self.vertical_sync_default
        self.driving_layer = self.ui_inputs.get(
            "vSyncTrack", {}).get("value") or self.driving_layer_default
        self.review_track = self.ui_inputs.get(
            "reviewTrack", {}).get("value") or self.review_track_default
        self.audio = self.ui_inputs.get(
            "audio", {}).get("value") or False

        # build subset name from layer name
        if self.subset_name == "[ track name ]":
            self.subset_name = self.track_name

        # create subset for publishing
        self.subset = self.subset_family + self.subset_name.capitalize()

    def _replace_hash_to_expression(self, name, text):
        """ Replace hash with number in correct padding. """
        _spl = text.split("#")
        _len = (len(_spl) - 1)
        _repl = "{{{0}:0>{1}}}".format(name, _len)
        return text.replace(("#" * _len), _repl)

    def _convert_to_marker_data(self):
        """ Convert internal data to marker data.

        Populating the marker data into internal variable self.marker_data
        """
        # define vertical sync attributes
        hero_track = True
        self.review_layer = ""
        if self.vertical_sync and self.track_name not in self.driving_layer:
            # if it is not then define vertical sync as None
            hero_track = False

        # increasing steps by index of rename iteration
        if not self.index_from_segment:
            self.count_steps *= self.rename_index

        hierarchy_formating_data = {}
        hierarchy_data = deepcopy(self.hierarchy_data)
        _data = self.current_segment_default_data.copy()
        if self.ui_inputs:
            # adding tag metadata from ui
            for _k, _v in self.ui_inputs.items():
                if _v["target"] == "tag":
                    self.marker_data[_k] = _v["value"]

            # driving layer is set as positive match
            if hero_track or self.vertical_sync:
                # mark review layer
                if self.review_track and (
                        self.review_track not in self.review_track_default):
                    # if review layer is defined and not the same as defalut
                    self.review_layer = self.review_track

                # shot num calculate
                if self.index_from_segment:
                    # use clip index from timeline
                    self.shot_num = self.count_steps * self.cs_index
                else:
                    if self.rename_index == 0:
                        self.shot_num = self.count_from
                    else:
                        self.shot_num = self.count_from + self.count_steps

            # clip name sequence number
            _data.update({"shot": self.shot_num})

            # solve # in test to pythonic expression
            for _k, _v in hierarchy_data.items():
                if "#" not in _v["value"]:
                    continue
                hierarchy_data[
                    _k]["value"] = self._replace_hash_to_expression(
                        _k, _v["value"])

            # fill up pythonic expresisons in hierarchy data
            for k, _v in hierarchy_data.items():
                hierarchy_formating_data[k] = _v["value"].format(**_data)
        else:
            # if no gui mode then just pass default data
            hierarchy_formating_data = hierarchy_data

        tag_hierarchy_data = self._solve_tag_hierarchy_data(
            hierarchy_formating_data
        )

        tag_hierarchy_data.update({"heroTrack": True})
        if hero_track and self.vertical_sync:
            self.vertical_clip_match.update({
                (self.clip_in, self.clip_out): tag_hierarchy_data
            })

        if not hero_track and self.vertical_sync:
            # driving layer is set as negative match
            for (_in, _out), hero_data in self.vertical_clip_match.items():
                hero_data.update({"heroTrack": False})
                if _in == self.clip_in and _out == self.clip_out:
                    data_subset = hero_data["subset"]
                    # add track index in case duplicity of names in hero data
                    if self.subset in data_subset:
                        hero_data["subset"] = self.subset + str(
                            self.track_index)
                    # in case track name and subset name is the same then add
                    if self.subset_name == self.track_name:
                        hero_data["subset"] = self.subset
                    # assing data to return hierarchy data to tag
                    tag_hierarchy_data = hero_data

        # add data to return data dict
        self.marker_data.update(tag_hierarchy_data)

    def _solve_tag_hierarchy_data(self, hierarchy_formating_data):
        """ Solve marker data from hierarchy data and templates. """
        # fill up clip name and hierarchy keys
        hierarchy_filled = self.hierarchy.format(**hierarchy_formating_data)
        clip_name_filled = self.clip_name.format(**hierarchy_formating_data)

        # remove shot from hierarchy data: is not needed anymore
        hierarchy_formating_data.pop("shot")

        return {
            "newClipName": clip_name_filled,
            "hierarchy": hierarchy_filled,
            "parents": self.parents,
            "hierarchyData": hierarchy_formating_data,
            "subset": self.subset,
            "family": self.subset_family,
            "families": [self.family]
        }

    def _convert_to_entity(self, type, template):
        """ Converting input key to key with type. """
        # convert to entity type
        entity_type = self.types.get(type, None)

        assert entity_type, "Missing entity type for `{}`".format(
            type
        )

        # first collect formating data to use for formating template
        formating_data = {}
        for _k, _v in self.hierarchy_data.items():
            value = _v["value"].format(
                **self.current_segment_default_data)
            formating_data[_k] = value

        return {
            "entity_type": entity_type,
            "entity_name": template.format(
                **formating_data
            )
        }

    def _create_parents(self):
        """ Create parents and return it in list. """
        self.parents = []

        patern = re.compile(self.parents_search_patern)

        par_split = [(patern.findall(t).pop(), t)
                     for t in self.hierarchy.split("/")]

        for type, template in par_split:
            parent = self._convert_to_entity(type, template)
            self.parents.append(parent)


# Publishing plugin functions

# Loader plugin functions
class ClipLoader(LoaderPlugin):
    """A basic clip loader for Flame

    This will implement the basic behavior for a loader to inherit from that
    will containerize the reference and will implement the `remove` and
    `update` logic.

    """

    options = [
        qargparse.Boolean(
            "handles",
            label="Set handles",
            default=0,
            help="Also set handles to clip as In/Out marks"
        )
    ]


class OpenClipSolver(flib.MediaInfoFile):
    create_new_clip = False

    log = log

    def __init__(self, openclip_file_path, feed_data):
        self.out_file = openclip_file_path

        # new feed variables:
        feed_path = feed_data.pop("path")

        # initialize parent class
        super(OpenClipSolver, self).__init__(
            feed_path,
            **feed_data
        )

        # get other metadata
        self.feed_version_name = feed_data["version"]
        self.feed_colorspace = feed_data.get("colorspace")
        self.log.debug("feed_version_name: {}".format(self.feed_version_name))

        # derivate other feed variables
        self.feed_basename = os.path.basename(feed_path)
        self.feed_dir = os.path.dirname(feed_path)
        self.feed_ext = os.path.splitext(self.feed_basename)[1][1:].lower()
        self.log.debug("feed_ext: {}".format(self.feed_ext))
        self.log.debug("out_file: {}".format(self.out_file))
        if not self._is_valid_tmp_file(self.out_file):
            self.create_new_clip = True

    def _is_valid_tmp_file(self, file):
        # check if file exists
        if os.path.isfile(file):
            # test also if file is not empty
            with open(file) as f:
                lines = f.readlines()

            if len(lines) > 2:
                return True

            # file is probably corrupted
            os.remove(file)
            return False

    def make(self):

        if self.create_new_clip:
            # New openClip
            self._create_new_open_clip()
        else:
            self._update_open_clip()

    def _clear_handler(self, xml_object):
        for handler in xml_object.findall("./handler"):
            self.log.info("Handler found")
            xml_object.remove(handler)

    def _create_new_open_clip(self):
        self.log.info("Building new openClip")
        self.log.debug(">> self.clip_data: {}".format(self.clip_data))

        # clip data comming from MediaInfoFile
        tmp_xml_feeds = self.clip_data.find('tracks/track/feeds')
        tmp_xml_feeds.set('currentVersion', self.feed_version_name)
        for tmp_feed in tmp_xml_feeds:
            tmp_feed.set('vuid', self.feed_version_name)

            # add colorspace if any is set
            if self.feed_colorspace:
                self._add_colorspace(tmp_feed, self.feed_colorspace)

            self._clear_handler(tmp_feed)

        tmp_xml_versions_obj = self.clip_data.find('versions')
        tmp_xml_versions_obj.set('currentVersion', self.feed_version_name)
        for xml_new_version in tmp_xml_versions_obj:
            xml_new_version.set('uid', self.feed_version_name)
            xml_new_version.set('type', 'version')

        self._clear_handler(self.clip_data)
        self.log.info("Adding feed version: {}".format(self.feed_basename))

        self.write_clip_data_to_file(self.out_file, self.clip_data)

    def _update_open_clip(self):
        self.log.info("Updating openClip ..")

        out_xml = ET.parse(self.out_file)
        out_xml = out_xml.getroot()

        self.log.debug(">> out_xml: {}".format(out_xml))
        self.log.debug(">> self.clip_data: {}".format(self.clip_data))

        # Get new feed from tmp file
        tmp_xml_feed = self.clip_data.find('tracks/track/feeds/feed')

        self._clear_handler(tmp_xml_feed)

        # update fps from MediaInfoFile class
        if self.fps:
            tmp_feed_fps_obj = tmp_xml_feed.find(
                "startTimecode/rate")
            tmp_feed_fps_obj.text = str(self.fps)

        # update start_frame from MediaInfoFile class
        if self.start_frame:
            tmp_feed_nb_ticks_obj = tmp_xml_feed.find(
                "startTimecode/nbTicks")
            tmp_feed_nb_ticks_obj.text = str(self.start_frame)

        # update drop_mode from MediaInfoFile class
        if self.drop_mode:
            tmp_feed_drop_mode_obj = tmp_xml_feed.find(
                "startTimecode/dropMode")
            tmp_feed_drop_mode_obj.text = str(self.drop_mode)

        new_path_obj = tmp_xml_feed.find(
            "spans/span/path")
        new_path = new_path_obj.text

        feed_added = False
        if not self._feed_exists(out_xml, new_path):
            tmp_xml_feed.set('vuid', self.feed_version_name)
            # Append new temp file feed to .clip source out xml
            out_track = out_xml.find("tracks/track")
            # add colorspace if any is set
            if self.feed_colorspace:
                self._add_colorspace(tmp_xml_feed, self.feed_colorspace)

            out_feeds = out_track.find('feeds')
            out_feeds.set('currentVersion', self.feed_version_name)
            out_feeds.append(tmp_xml_feed)

            self.log.info(
                "Appending new feed: {}".format(
                    self.feed_version_name))
            feed_added = True

        if feed_added:
            # Append vUID to versions
            out_xml_versions_obj = out_xml.find('versions')
            out_xml_versions_obj.set(
                'currentVersion', self.feed_version_name)
            new_version_obj = ET.Element(
                "version", {"type": "version", "uid": self.feed_version_name})
            out_xml_versions_obj.insert(0, new_version_obj)

            self._clear_handler(out_xml)

            # fist create backup
            self._create_openclip_backup_file(self.out_file)

            self.log.info("Adding feed version: {}".format(
                self.feed_version_name))

            self.write_clip_data_to_file(self.out_file, out_xml)

            self.log.debug("OpenClip Updated: {}".format(self.out_file))

    def _feed_exists(self, xml_data, path):
        # loop all available feed paths and check if
        # the path is not already in file
        for src_path in xml_data.iter('path'):
            if path == src_path.text:
                self.log.warning(
                    "Not appending file as it already is in .clip file")
                return True

    def _create_openclip_backup_file(self, file):
        bck_file = "{}.bak".format(file)
        # if backup does not exist
        if not os.path.isfile(bck_file):
            shutil.copy2(file, bck_file)
        else:
            # in case it exists and is already multiplied
            created = False
            for _i in range(1, 99):
                bck_file = "{name}.bak.{idx:0>2}".format(
                    name=file,
                    idx=_i)
                # create numbered backup file
                if not os.path.isfile(bck_file):
                    shutil.copy2(file, bck_file)
                    created = True
                    break
            # in case numbered does not exists
            if not created:
                bck_file = "{}.bak.last".format(file)
                shutil.copy2(file, bck_file)

    def _add_colorspace(self, feed_obj, profile_name):
        feed_storage_obj = feed_obj.find("storageFormat")
        feed_clr_obj = feed_storage_obj.find("colourSpace")
        if feed_clr_obj is not None:
            feed_clr_obj = ET.Element(
                "colourSpace", {"type": "string"})
            feed_storage_obj.append(feed_clr_obj)

        feed_clr_obj.text = profile_name
