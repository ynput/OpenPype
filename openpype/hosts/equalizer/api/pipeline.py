from attrs import field, define
from openpype.pipeline import AVALON_CONTAINER_ID


@define
class Container(object):

    name: str = field(default=None)
    id: str = field(init=False, default=AVALON_CONTAINER_ID)
    namespace: str = field(default="")
    loader: str = field(default=None)
    representation: str = field(default=None)
