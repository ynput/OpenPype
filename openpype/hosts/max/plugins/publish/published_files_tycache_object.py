import pyblish.api
from pymxs import runtime as rt


class PublishedFilesTycacheObject(pyblish.api.InstancePlugin):
    """Load Published Files for Created TyCache Object."""

    order = pyblish.api.IntegratorOrder + 0.89
    label = "Published files for tycache Object"
    hosts = ["max"]
    families = ["tycache"]

    def process(self, instance):
        tycache_attrs = instance.data["tyc_attrs"]
        if "tycacheCreateObjectIfNotCreated" not in (
            tycache_attrs["tycacheAttributes"]):
            self.log.debug("Attribute of 'Create Tycache Object' and "
                           "'Only if one does not already exists' "
                           "not being enabled. \n\n"
                           "Skipping using published file as tyCache Object.")
            return

        published_path = None
        tycache_object_name = tycache_attrs["tycacheObjectName"]
        representation = instance.data["representations"]
        for repre in representation:
            published_path = repre["published_path"]

        if "$(tyFlowName)" in tycache_object_name:
            name = next(member.name for member in instance.data["members"])
            tycache_object_name = tycache_object_name.replace(
                "$(tyFlowName)", name)
            tycache_object_node = rt.GetNodeByName(tycache_object_name)
            if tycache_object_node:
                tycache_object_node.filename = (
                    published_path.replace("\\", "/")
                )
