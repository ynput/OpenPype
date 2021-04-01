from avalon import houdini
from openpype.api import PypeCreatorMixin


class Creator(PypeCreatorMixin, houdini.Creator):
    pass
