from pype.hosts import hiero as phiero
from collections import OrderedDict
from pype.hosts.hiero import plugin, lib
from pprint import pformat
reload(plugin)
reload(phiero)
reload(lib)


class CreateShotClip(phiero.Creator):
    """Publishable clip"""

    label = "Shot"
    family = "clip"
    icon = "film"
    defaults = ["Main"]

    gui_name = "Pype sequencial rename with hirerarchy"
    gui_info = "Define sequencial rename and fill hierarchy data."
    gui_inputs = [
        {"hierarchyData": {
            "value": {
                "folder": {"value": "shots", "type": "QLineEdit",
                           "label": "Folder", "target": "tag", "toolTip": "name of folder used for root of generated shots"},   # noqa
                "shot": {"value": "sh####", "type": "QLineEdit",
                         "label": "Shot", "target": "tag"},
                "track": {"value": "{track}", "type": "QLineEdit",
                          "label": "Track (Layer) Name", "target": "tag"},
                "sequence": {"value": "sc010", "type": "QLineEdit",
                             "label": "Sequence Name", "target": "tag"},
                "episode": {"value": "ep01", "type": "QLineEdit",
                            "label": "Episode Name", "target": "tag"}
            },
            "type": "dict",
            "label": "Hierarchy Data Parents segments",
            "target": "tag"}
         },
        {"templates": {
            "value": {
                "clipName": {"value": "{episode}{sequence}{shot}",
                             "type": "QLineEdit", "label": "Clip Name Template", "target": "tag", "toolTip": "template for creating shot namespace used for renaming (use rename: on)"},  # noqa
                "hierarchy": {"value": "{folder}/{episode}/{sequence}",
                              "type": "QLineEdit", "label": "Shot Parent Hierarchy", "target": "tag", "toolTip": "Parents folder for shot root folder, Template filled with `Hierarchy Data` section"}  # noqa
            },
            "type": "section",
            "label": "Hierarchy and shot name template",
            "target": "ui"
         }},
        {"renameAttr": {
            "value": {
                "clipRename": {"value": True, "type": "QCheckBox",
                          "label": "Rename clips", "target": "ui", "toolTip": "Renaming selected clips on fly"},   # noqa
                "countFrom": {"value": 10, "type": "QSpinBox",
                              "label": "Count sequence from", "target": "ui", "toolTip": "Set when the sequence number starts from"},   # noqa
                "countSteps": {"value": 10, "type": "QSpinBox",
                          "label": "Stepping number", "target": "ui", "toolTip": "What number is adding every new step"}   # noqa
            },
            "type": "section",
            "label": "Sequencial reaming properties",
            "target": "ui"
         }},
        {"shotAttr": {
            "value": {
                "workfileFrameStart": {"value": 1001, "type": "QSpinBox",
                              "label": "Workfiles Start Frame", "target": "tag", "toolTip": "Set workfile starting frame number"},   # noqa
                "handleStart": {"value": 0, "type": "QSpinBox",
                          "label": "Handle Start", "target": "tag", "toolTip": "Handle at start of clip"},   # noqa
                "handleEnd": {"value": 0, "type": "QSpinBox",
                          "label": "Handle End", "target": "tag", "toolTip": "Handle at end of clip"}   # noqa
            },
            "type": "section",
            "label": "Shot ranges ",
            "target": "ui"
         }},
        {"shotAttr": {
            "value": {
                "subsetName": {"value": ["main", "<track_name>"],
                               "type": "QComboBox",
                               "label": "Subset Name", "target": "tag", "toolTip": "chose subset name patern, if <track_name> is selected, name of track layer will be used"},   # noqa
                "subsetFamily": {"value": ["plate", "take"],
                                 "type": "QComboBox",
                                 "label": "Subset Family", "target": "tag", "toolTip": "What use of this subset is for"},   # noqa
                "previewOn": {"value": True, "type": "QCheckBox",
                          "label": "Generate Preview video", "target": "tag", "toolTip": "Generate preview videos on fly"},   # noqa
                "audioOn": {"value": False, "type": "QCheckBox",
                          "label": "Include Audio", "target": "tag", "toolTip": "Process subsets with corresponding audio"}   # noqa
            },
            "type": "section",
            "label": "Shot ranges ",
            "target": "ui"
         }}
    ]
    presets = None

    def process(self):
        # solve gui inputs overwrites from presets
        # overwrite gui inputs from presets
        new_inputs = OrderedDict()
        for input_widget in self.gui_inputs:
            new_inputs.update(input_widget)
        # get key pares from presets and match it on ui inputs
        for k, v in new_inputs.items():
            if v["type"] in ("dict", "section"):
                # nested dictionary (only one level allowed)
                for _k, _v in v["value"].items():
                    if self.presets.get(_k):
                        new_inputs[k]["value"][_k]["value"] = self.presets[_k]
            if self.presets.get(k):
                new_inputs[k]["value"] = self.presets[k]

        print(">> new_inputs", pformat((new_inputs)))
        # open widget for plugins inputs
        widget = self.widget(self.gui_name, self.gui_info, new_inputs)
        widget.exec_()

        self.log.debug("__ selected_clips: {}".format(self.selected))
        if len(self.selected) < 1:
            return

        if not widget.result:
            print("Operation aborted")
            return

        print("__ widget.result: {}".format(widget.result))

        self.rename_add = 0
        for i, track_item in enumerate(self.selected):
            self.rename_index = i

            # convert track item to timeline media pool item
            phiero.create_publish_clip(
                self,
                track_item,
                rename=True,
                **dict({"ui_inputs": widget.result})
            )
