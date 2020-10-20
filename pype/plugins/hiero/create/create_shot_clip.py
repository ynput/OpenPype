from pprint import pformat
from pype.hosts import hiero as phiero
from collections import OrderedDict
from pype.hosts.hiero import plugin, lib

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
            "folder": "shots",
            "shot": "sh####",
            "track": "{track}",
            "sequence": "sc010",
            "episode": "ep01"
        }},
        {"clipName": "{episode}{sequence}{shot}"},
        {"hierarchy": "{folder}/{sequence}/{shot}"},
        {"countFrom": 10},
        {"steps": 10},
        {"workfileFrameStart": 1001},
        {"handleStart": 0},
        {"handleEnd": 0},
        {"subsetName": ["main", "<track_name>"]},
        {"subsetFamily": ["plate", "take"]},
        {"audioOn": True},
        {"previewOn": True}
    ]
    presets = None

    def process(self):
        # solve gui inputs overwrites from presets
        # overwrite gui inputs from presets
        new_inputs = OrderedDict()
        for input_widget in self.gui_inputs:
            new_inputs.update(input_widget)
        for k, v in new_inputs.items():
            if isinstance(v, dict):
                # nested dictionary (only one level allowed)
                for _k, _v in v.items():
                    if self.presets.get(_k):
                        new_inputs[k][_k] = self.presets[_k]
            if self.presets.get(k):
                new_inputs[k] = self.presets[k]

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
                **dict({"presets": widget.result})
            )
