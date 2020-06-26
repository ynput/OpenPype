from pprint import pformat
from pype.hosts import resolve
from pype.hosts.resolve import lib


class CreateShotClip(resolve.Creator):
    """Publishable clip"""

    label = "Shot"
    family = "clip"
    icon = "film"
    defaults = ["Main"]

    gui_name = "Define sequencial rename"
    presets = None

    def process(self):
        print(f"__ selected_clips: {self.selected}")

        if len(self.selected) < 1:
            return

        widget = self.widget(self.gui_name, self.presets)
        widget.exec_()

        print(widget.result)
        if widget.result:
            print("success")
            return
        else:
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
            print(t_data)
            # convert track item to timeline media pool item
            c_clip = resolve.create_compound_clip(
                t_data, mp_folder, rename=True, **dict(
                    {"presets": self.presets}))
