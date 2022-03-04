import pyblish.api
import bpy
from openpype.hosts.blender.api import plugin
from openpype.hosts.blender.api.workio import save_file
from openpype.hosts.blender.api.pipeline import (
    AVALON_CONTAINERS,
    AVALON_PROPERTY,
    AVALON_CONTAINER_ID,
)
from avalon import io


class UpdateAvalonProperty(pyblish.api.InstancePlugin):
    """Update Avalon Property with representation"""

    order = pyblish.api.IntegratorOrder + 0.05
    label = "Update Avalon Property"
    optional = False
    hosts = ["blender"]
    families = ["animation", "model", "rig", "action", "layout"]

    def process(self, instance):

        from openpype.lib import version_up

        libpath = ""
        # Get representation from the db
        representation = io.find_one(
            {
                "context.asset": instance.data["anatomyData"]["asset"],
                "context.family": instance.data["anatomyData"]["family"],
                "context.version": int(instance.data["anatomyData"]["version"]),
                "context.ext": "blend",
            }
        )
        # Get the avalon container in the scene
        container_collection = None
        instances = plugin.get_instances_list()
        for data_collection in instances:
            if data_collection.override_library is None:
                container_collection = data_collection

        # Set the avalon property with the representation data
        container_collection[AVALON_PROPERTY] = {
            "schema": "openpype:container-2.0",
            "id": AVALON_CONTAINER_ID,
            # "original_container_name": self.original_container_name,
            "name": str(representation["context"]["asset"]),
            "namespace": str(representation["context"]["asset"]),
            "loader": str(self.__class__.__name__),
            "representation": str(representation["_id"]),
            "libpath": str(representation["data"]["path"]),
            "asset_name": str(representation["context"]["asset"]),
            "parent": str(representation["parent"]),
            "family": str(representation["context"]["family"]),
            "objectName": container_collection.name,
        }
        # Get the filepath of the publish
        filepath = str(representation["data"]["path"])

        # Get the filepath of the publish
        save_file(filepath, copy=False)

        # Overwrite the publish file
        self.log.info(" %s updated.", filepath)


# {
#     "_id": ObjectId("622203885e50300d1667d7ed"),
#     "schema": "openpype:representation-2.0",
#     "type": "representation",
#     "parent": ObjectId("622203875e50300d1667d7ec"),
#     "name": "blend",
#     "data": {
#         "path": "C:\\projects\\Woolly\\Character\\Mickey\\publish\\model\\modelDefault\\v051\\woolly_Mickey_modelDefault_v051.blend",
#         "template": "{root[work]}\\{project[name]}\\{hierarchy}\\{asset}\\publish\\{family}\\{subset}\\v{version:0>3}\\{project[code]}_{asset}_{subset}_v{version:0>3}<_{output}><.{frame:0>4}><_{udim}>.{ext}",
#     },
#     "dependencies": [],
#     "context": {
#         "root": {"work": "C:/projects"},
#         "project": {"name": "Woolly", "code": "woolly"},
#         "hierarchy": "Character",
#         "asset": "Mickey",
#         "family": "model",
#         "subset": "modelDefault",
#         "version": 51,
#         "ext": "blend",
#         "task": {"name": "Modeling", "type": "Modeling", "short": "mdl"},
#         "representation": "blend",
#         "username": "Dimitri",
#     },
#     "files": [
#         {
#             "_id": ObjectId("622203885e50300d1667d7ef"),
#             "path": "{root[work]}/Woolly/Character/Mickey/publish/model/modelDefault/v051/woolly_Mickey_modelDefault_v051.blend",
#             "size": 117348,
#             "hash": "woolly_Mickey_modelDefault_v051,blend|1646396295,8367813|117348",
#             "sites": [
#                 {
#                     "name": "studio",
#                     "created_dt": datetime.datetime(2022, 3, 4, 13, 18, 16, 86000),
#                 }
#             ],
#         }
#     ],
# }
# {root[work]}\{project[name]}\{hierarchy}\{asset}\publish\{family}\{subset}\v{version:0>3}\{project[code]}_{asset}_{subset}_v{version:0>3}<_{output}><.{frame:0>4}><_{udim}>.{ext}
