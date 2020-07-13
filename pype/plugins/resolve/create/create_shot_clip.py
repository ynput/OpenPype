from pprint import pformat
from pype.hosts import resolve
from pype.hosts.resolve import lib


class CreateShotClip(resolve.Creator):
    """Publishable clip"""

    label = "Shot"
    family = "clip"
    icon = "film"
    defaults = ["Main"]

    gui_name = "Pype sequencial rename with hirerarchy"
    gui_info = "Define sequencial rename and fill hierarchy data."
    gui_inputs = {
        "clipName": "{episode}{sequence}{shot}",
        "hierarchy": "{folder}/{sequence}/{shot}",
        "countFrom": 10,
        "steps": 10,
        "hierarchyData": {
            "folder": "shots",
            "shot": "sh####",
            "track": "{track}",
            "sequence": "sc010",
            "episode": "ep01"
        }
    }
    presets = None

    def process(self):
        # solve gui inputs overwrites from presets
        # overwrite gui inputs from presets
        for k, v in self.gui_inputs.items():
            if isinstance(v, dict):
                # nested dictionary (only one level allowed)
                for _k, _v in v.items():
                    if self.presets.get(_k):
                        self.gui_inputs[k][_k] = self.presets[_k]
            if self.presets.get(k):
                self.gui_inputs[k] = self.presets[k]

        # open widget for plugins inputs
        widget = self.widget(self.gui_name, self.gui_info, self.gui_inputs)
        widget.exec_()

        print(f"__ selected_clips: {self.selected}")
        if len(self.selected) < 1:
            return

        if not widget.result:
            print("Operation aborted")
            return

        # sequence attrs
        sq_frame_start = self.sequence.GetStartFrame()
        sq_markers = self.sequence.GetMarkers()
        print(f"__ sq_frame_start: {pformat(sq_frame_start)}")
        print(f"__ seq_markers: {pformat(sq_markers)}")

        # create media bin for compound clips (trackItems)
        mp_folder = resolve.create_current_sequence_media_bin(self.sequence)
        print(f"_ mp_folder: {mp_folder.GetName()}")

        lib.rename_add = 0
        for i, t_data in enumerate(self.selected):
            lib.rename_index = i

            # clear color after it is done
            t_data["clip"]["item"].ClearClipColor()

            # convert track item to timeline media pool item
            resolve.create_compound_clip(
                t_data,
                mp_folder,
                rename=True,
                **dict(
                    {"presets": widget.result})
            )
