from openpype.hosts.maya.api import lib, plugin


class CreateAnimLib(plugin.Creator):
    """Studio Library animlib"""

    name = "animlibDefault"
    label = "AnimLib"
    family = "animlib"
    icon = "wheelchair"
    defaults = ["Main"]

    def __init__(self, *args, **kwargs):
        super(CreateAnimLib, self).__init__(*args, **kwargs)

        # get basic animation data : start / end / handles / steps
        anim_data = lib.collect_animation_data()
        anim_data.pop("step")
        anim_data.pop("handles")
        for key, value in anim_data.items():
            self.data[key] = value

        # time = mutils.selectedObjectsFrameRange(objects)
        # start, end = time
        # # Check frame range
        # if start is None or end is None:
        #     msg = "Please specify a start and end frame!"
        #     raise AnimationTransferError(msg)
        # self.data["start"] = start
        # self.data["end"] = end
