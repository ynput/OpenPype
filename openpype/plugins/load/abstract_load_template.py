import avalon.api
import avalon.io
from avalon.maya.pipeline import containerise
from avalon.maya import lib
from maya import cmds, mel
from avalon import maya
import avalon
from openpype.lib.profiles_filtering import filter_profiles
from openpype.settings import get_project_settings

class AbstractTemplateLoader:

    def __init__(self, task) -> None:
        self.task = task
        self.get_template()

    @with_avalon
    def get_build_profiles(task_type):
        host_name = avalon.io.Session["AVALON_APP"]
        project_settings = get_project_settings(
            avalon.io.Session["AVALON_PROJECT"]
        )

        wb_settings = project_settings.get(host_name, {}).get("workfile_builder")
        # Get presets for host

        if not wb_settings:
            # backward compatibility
            wb_settings = host_settings.get("workfile_build") or {}

        builder_profiles = wb_settings.get("profiles")
        if not builder_profiles:
            return None

        return filter_profiles(builder_profiles, {"task_type": task_type})

    def get_template_path(self):
        # Get template from avalon context


        self.template_path = ''

    def load_template(self):
        raise NotImplementedError

# Maya api
class TemplateLoader:
    def load_template(self):
        self.context_assets = []
        self.linked_assets = []

        with maya.maintained_selection():
            nodes = cmds.file(self.template_path,
                      i=True,
                      preserveReferences=True,
                      returnNewNodes=True,
                      groupReference=True,
                     )
        return self.get_template_nodes()

    def get_template_nodes(self):
        nodes = cmds.ls(type='locator')
        context_assets = []
        linked_assets = []

        for node in nodes: ### '&&&' Nom des variables à décider
            if not cmds.has_attr("&&&Loader Pref"):
                continue
            elif cmds.getAttr("&&&Loader pref") == '&&&Context':
                context_assets.append(node)
            elif cmds.getAttr("&&&Loader pref") == "&&&Linked":
                linked_assets.append(node)
        return context_assets, linked_assets


# class AbstractTemplateLoader:
#     """Abstract loader for templating files"""

#     families = []
#     # icon = "volume-up"
#     # color = "orange"

#     #@with_avalon
#     def get_build_profiles(task_type):
#         host_name = avalon.api.registered_host().__name__.rsplit(".", 1)[-1]
#         project_settings = get_project_settings(
#             avalon.io.Session["AVALON_PROJECT"]
#         )

#         host_settings = project_settings.get(host_name) or {}
#         # Get presets for host
#         wb_settings = host_settings.get("workfile_builder")
#         if not wb_settings:
#             # backward compatibility
#             wb_settings = host_settings.get("workfile_build") or {}

#         builder_profiles = wb_settings.get("profiles")
#         if not builder_profiles:
#             return None

#         return filter_profiles(builder_profiles, {"task_type": task_type})

#     def load_template(self):
#         raise NotImplementedError('Not implemented in your DCC pleas contact your TD.')

#     def load(self, context, name=None, namespace=None, data=None):
#         print("3")
#         # Get current asset name and entity
#         current_asset_name = context.get('asset')
#         current_asset_entity = avalon.io.find_one({
#             "type": "asset",
#             "name": current_asset_name
#         })
#         # Get current task name
#         current_task_name = avalon.io.Session.get("AVALON_TASK", {})

#         # Skip if asset was not found
#         if not current_asset_entity:
#             print("Asset entity with name `{}` was not found".format(
#                 current_asset_name
#             ))
#             return

#         # Load workfile presets for task
#         self.build_profiles = self.get_build_profiles(
#             current_task_name.get('type'))

#         # Skip if there are any presets for task
#         if not self.build_presets:
#             self.log.warning(
#                 "Current task `{}` does not have any loading preset.".format(
#                     current_task_name
#                 )
#             )
#             return
#         print("4'")
#         # Prepare available loaders
#         loaders_by_name = {}
#         for loader in avalon.api.discover(avalon.api.Loader):
#             loader_name = loader.__name__
#             if loader_name in loaders_by_name:
#                 raise KeyError(
#                     "Duplicated loader name {0}!".format(loader_name)
#                 )
#             loaders_by_name[loader_name] = loader

#         template_loader = loaders_by_name.get('TemplateLoader')

#         # Skip if there are any loaders
#         if not loaders_by_name:
#             self.log.warning("There are no registered loaders.")
#             return

#         # Skip if there are not template loaders
#         if not template_loader:
#             self.log.error("There are no registered template loader.")
#             return

#         # Get template for current task
#         template_path = self.build_presets.get("template_path")
#         if not template_path:
#             self.log.warning(
#                 "Current task `{}` has no defined template.".format(
#                     current_task_name
#                 )
#             )
#             return
#         self.template_path = resolve(template_path)
#         #TODO: resolve path
#         if not os.path.exits(template_path):
#             self.log.warning(
#                 "Template path: `{}` not found.".format(
#                     current_task_name
#                 )
#             )
#             return
#         print("5")
#         self.load_template()


#     def update(self, container, representation):
#         node = container["objectName"]

#         path = avalon.api.get_representation_path(representation)

#         cmds.file(path, type="mayaAscii", i=True, returnNewNodes=True, defaultNamespace=container['namespace'])
