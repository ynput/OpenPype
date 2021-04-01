from openpype.api import PypeCreatorMixin
from avalon.tvpaint import pipeline


class Creator(PypeCreatorMixin, pipeline.Creator):
    pass
