import nuke
from openpype.pipeline import load


class MatchmoveLoader(load.LoaderPlugin):
    """
    This will run matchmove script to create track in script.
    """

    families = ["matchmove"]
    representations = ["*"]
    extensions = {"py"}

    defaults = ["Camera", "Object"]

    label = "Run matchmove script"
    icon = "empire"
    color = "orange"

    def load(self, context, name, namespace, data):
        path = self.filepath_from_context(context)
        if path.lower().endswith(".py"):
            exec(open(path).read())

        else:
            msg = "Unsupported script type"
            self.log.error(msg)
            nuke.message(msg)

        return True
