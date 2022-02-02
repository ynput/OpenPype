from avalon import harmony
from openpype.api import PypeCreatorMixin


class Creator(PypeCreatorMixin, harmony.Creator):
    defaults = ["Main"]
