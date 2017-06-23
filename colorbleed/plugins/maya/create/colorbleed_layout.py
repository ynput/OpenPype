import avalon.maya


class CreateLayout(avalon.maya.Creator):
    """The layout of a episode / sequence / shot """

    name = "layoutDefault"
    label = "Layout"
    family = "colorbleed.layout"

    def __init__(self, *args, **kwargs):
        super(CreateLayout, self).__init__(*args, **kwargs)
        from maya import cmds

        self.data.update({
            "startFrame": lambda: cmds.playbackOptions(
                query=True, animationStartTime=True),
            "endFrame": lambda: cmds.playbackOptions(
                query=True, animationEndTime=True),
        })
