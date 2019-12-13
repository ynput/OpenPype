from avalon import api


class MatchmoveLoader(api.Loader):
    """
    This will run matchmove script to create track in script.
    """

    families = ["matchmove"]
    representations = ["py"]
    defaults = ["Camera", "Object"]

    label = "Run matchmove script"
    icon = "empire"
    color = "orange"

    def load(self, context, name, namespace, data):
        if self.fname.lower().endswith(".py"):
            exec(open(self.fname).read())

        else:
            self.log.error("Unsupported script type")

        return True
