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
    gui_inputs = {
        "hierarchyData": {
                "value": {
                    "folder": {"value": "shots", "type": "QLineEdit",
                               "label": "{folder}", "target": "tag",
                               "toolTip": "Name of folder used for root of generated shots.\nUsable tokens:\n\t{_clip_}: name of used clip\n\t{_track_}: name of parent track layer\n\t{_sequence_}: name of parent sequence (timeline)",  # noqa
                                "order": 0},
                    "episode": {"value": "ep01", "type": "QLineEdit",
                                "label": "{episode}", "target": "tag",
                                "toolTip": "Name of episode.\nUsable tokens:\n\t{_clip_}: name of used clip\n\t{_track_}: name of parent track layer\n\t{_sequence_}: name of parent sequence (timeline)",  # noqa
                                "order": 1},
                    "sequence": {"value": "sc010", "type": "QLineEdit",
                                 "label": "{sequence}", "target": "tag",
                                 "toolTip": "Name of sequence of shots.\nUsable tokens:\n\t{_clip_}: name of used clip\n\t{_track_}: name of parent track layer\n\t{_sequence_}: name of parent sequence (timeline)",  # noqa
                                 "order": 2},
                    "shot": {"value": "sh####", "type": "QLineEdit",
                             "label": "{shot}", "target": "tag",
                             "toolTip": "Name of shot. `#` is converted to paded number. \nAlso could be used with usable tokens:\n\t{_clip_}: name of used clip\n\t{_track_}: name of parent track layer\n\t{_sequence_}: name of parent sequence (timeline)",  # noqa
                             "order": 3}
                },
                "type": "dict",
                "label": "Hierarchy Data Parents segments",
                "target": "tag",
                "order": 0
        },
        "templates": {
            "value": {
                "hierarchy": {"value": "{folder}/{episode}/{sequence}",
                              "type": "QLineEdit", "label": "Shot Parent Hierarchy", "target": "tag", "toolTip": "Parents folder for shot root folder, Template filled with `Hierarchy Data` section",  # noqa
                               "order": 0}
            },
            "type": "section",
            "label": "Hierarchy and shot name template",
            "target": "ui",
            "order": 1
         },
        "renameAttr": {
            "value": {
                "clipRename": {"value": True, "type": "QCheckBox",
                          "label": "Rename clips", "target": "ui", "toolTip": "Renaming selected clips on fly",  # noqa
                           "order": 0},
                "clipName": {"value": "{episode}{sequence}{shot}",
                             "type": "QLineEdit", "label": "Clip Name Template", "target": "tag", "toolTip": "template for creating shot namespace used for renaming (use rename: on)",  # noqa
                              "order": 1},
                "countFrom": {"value": 10, "type": "QSpinBox",
                              "label": "Count sequence from", "target": "ui", "toolTip": "Set when the sequence number starts from",  # noqa
                               "order": 2},
                "countSteps": {"value": 10, "type": "QSpinBox",
                          "label": "Stepping number", "target": "ui", "toolTip": "What number is adding every new step",  # noqa
                           "order": 3},
            },
            "type": "section",
            "label": "Sequencial reaming properties",
            "target": "ui",
            "order": 2
         },
        "frameRangeAttr": {
            "value": {
                "workfileFrameStart": {"value": 1001, "type": "QSpinBox",
                              "label": "Workfiles Start Frame", "target": "tag", "toolTip": "Set workfile starting frame number",  # noqa
                              "order": 0},
                "handleStart": {"value": 0, "type": "QSpinBox",
                          "label": "Handle Start", "target": "tag", "toolTip": "Handle at start of clip",  # noqa
                           "order": 1},
                "handleEnd": {"value": 0, "type": "QSpinBox",
                          "label": "Handle End", "target": "tag", "toolTip": "Handle at end of clip",  # noqa
                           "order": 2},
            },
            "type": "section",
            "label": "Shot ranges ",
            "target": "ui",
            "order": 3
         },
        "shotAttr": {
            "value": {
                "subsetName": {"value": ["main", "<track_name>"],
                               "type": "QComboBox",
                               "label": "Subset Name", "target": "tag", "toolTip": "chose subset name patern, if <track_name> is selected, name of track layer will be used",  # noqa
                                "order": 0},
                "subsetFamily": {"value": ["plate", "take"],
                                 "type": "QComboBox",
                                 "label": "Subset Family", "target": "tag", "toolTip": "What use of this subset is for",  # noqa
                                  "order": 1},
                "previewOn": {"value": True, "type": "QCheckBox",
                          "label": "Generate Preview video", "target": "tag", "toolTip": "Generate preview videos on fly",  # noqa
                           "order": 2},
                "audioOn": {"value": False, "type": "QCheckBox",
                          "label": "Include Audio", "target": "tag", "toolTip": "Process subsets with corresponding audio",  # noqa
                           "order": 3},
            },
            "type": "section",
            "label": "Shot ranges ",
            "target": "ui",
            "order": 4
         }
    }

    presets = None

    def process(self):
        # get key pares from presets and match it on ui inputs
        for k, v in self.gui_inputs.items():
            if v["type"] in ("dict", "section"):
                # nested dictionary (only one level allowed
                # for sections and dict)
                for _k, _v in v["value"].items():
                    if self.presets.get(_k):
                        self.gui_inputs[k][
                            "value"][_k]["value"] = self.presets[_k]
            if self.presets.get(k):
                self.gui_inputs[k]["value"] = self.presets[k]

        print(">> self.gui_inputs", pformat((self.gui_inputs)))
        # open widget for plugins inputs
        widget = self.widget(self.gui_name, self.gui_info, self.gui_inputs)
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
