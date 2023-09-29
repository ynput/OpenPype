import openpype.hosts.maya.api.plugin
import maya.cmds as cmds


def _process_reference(file_url, name, namespace, options):
    """Load files by referencing scene in Maya.

    Args:
        file_url (str): fileapth of the objects to be loaded
        name (str): subset name
        namespace (str): namespace
        options (dict): dict of storing the param

    Returns:
        list: list of object nodes
    """
    from openpype.hosts.maya.api.lib import unique_namespace
    # Get name from asset being loaded
    # Assuming name is subset name from the animation, we split the number
    # suffix from the name to ensure the namespace is unique
    name = name.split("_")[0]
    ext = file_url.split(".")[-1]
    namespace = unique_namespace(
        "{}_".format(name),
        format="%03d",
        suffix="_{}".format(ext)
    )

    attach_to_root = options.get("attach_to_root", True)
    group_name = options["group_name"]

    # no group shall be created
    if not attach_to_root:
        group_name = namespace

    nodes = cmds.file(file_url,
                      namespace=namespace,
                      sharedReferenceFile=False,
                      groupReference=attach_to_root,
                      groupName=group_name,
                      reference=True,
                      returnNewNodes=True)
    return nodes


class AbcLoader(openpype.hosts.maya.api.plugin.ReferenceLoader):
    """Loader to reference an Alembic file"""

    families = ["animation",
                "camera",
                "pointcache"]
    representations = ["abc"]

    label = "Reference animation"
    order = -10
    icon = "code-fork"
    color = "orange"

    def process_reference(self, context, name, namespace, options):

        cmds.loadPlugin("AbcImport.mll", quiet=True)
        # hero_001 (abc)
        # asset_counter{optional}
        path = self.filepath_from_context(context)
        file_url = self.prepare_root_value(path,
                                           context["project"]["name"])

        nodes = _process_reference(file_url, name, namespace, options)
        # load colorbleed ID attribute
        self[:] = nodes

        return nodes


class FbxLoader(openpype.hosts.maya.api.plugin.ReferenceLoader):
    """Loader to reference an Fbx files"""

    families = ["animation",
                "camera"]
    representations = ["fbx"]

    label = "Reference animation"
    order = -10
    icon = "code-fork"
    color = "orange"

    def process_reference(self, context, name, namespace, options):

        cmds.loadPlugin("fbx4maya.mll", quiet=True)

        path = self.filepath_from_context(context)
        file_url = self.prepare_root_value(path,
                                           context["project"]["name"])

        nodes = _process_reference(file_url, name, namespace, options)

        self[:] = nodes

        return nodes
