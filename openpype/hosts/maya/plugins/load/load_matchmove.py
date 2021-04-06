from avalon import api
from maya import mel


class MatchmoveLoader(api.Loader):
    """
    This will run matchmove script to create track in scene.

    Supported script types are .py and .mel
    """

    families = ["matchmove"]
    representations = ["py", "mel"]
    defaults = ["Camera", "Object", "Mocap"]

    label = "Run matchmove script"
    icon = "empire"
    color = "orange"

    def load(self, context, name, namespace, data):
        if self.fname.lower().endswith(".py"):
            exec(open(self.fname).read())

        elif self.fname.lower().endswith(".mel"):
            mel.eval('source "{}"'.format(self.fname))

        else:
            self.log.error("Unsupported script type")

        return True
