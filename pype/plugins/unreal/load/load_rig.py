from avalon import api, pipeline
from avalon.unreal import lib
from avalon.unreal import pipeline as unreal_pipeline
import unreal


class SkeletalMeshFBXLoader(api.Loader):
    """Load Unreal SkeletalMesh from FBX"""

    families = ["rig"]
    label = "Import FBX Skeletal Mesh"
    representations = ["fbx"]
    icon = "cube"
    color = "orange"

    def load(self, context, name, namespace, data):
        """
        Load and containerise representation into Content Browser.

        This is two step process. First, import FBX to temporary path and
        then call `containerise()` on it - this moves all content to new
        directory and then it will create AssetContainer there and imprint it
        with metadata. This will mark this path as container.

        Args:
            context (dict): application context
            name (str): subset name
            namespace (str): in Unreal this is basically path to container.
                             This is not passed here, so namespace is set
                             by `containerise()` because only then we know
                             real path.
            data (dict): Those would be data to be imprinted. This is not used
                         now, data are imprinted by `containerise()`.

        Returns:
            list(str): list of container content
        """

        # Create directory for asset and avalon container
        root = "/Game"
        asset = context.get('asset')
        asset_name = asset.get('name')
        if asset_name:
            container_name = "{}_{}".format(asset_name, name)
        else:
            container_name = "{}".format(name)

        tools = unreal.AssetToolsHelpers().get_asset_tools()
        asset_dir, avalon_asset_name = tools.create_unique_asset_name(
            "{}/{}".format(root, container_name), "_CON"
        )

        unreal.EditorAssetLibrary.make_directory(asset_dir)

        task = unreal.AssetImportTask()

        task.set_editor_property('filename', self.fname)
        task.set_editor_property('destination_path', asset_dir)
        task.set_editor_property('destination_name', container_name)
        task.set_editor_property('replace_existing', False)
        task.set_editor_property('automated', True)
        task.set_editor_property('save', False)

        # set import options here
        options = unreal.FbxImportUI()
        options.set_editor_property('import_as_skeletal', True)
        options.set_editor_property('import_animations', False)
        options.set_editor_property('import_mesh', True)
        options.set_editor_property('import_materials', True)
        options.set_editor_property('import_textures', True)
        options.set_editor_property('skeleton', None)
        options.set_editor_property('create_physics_asset', False)

        options.set_editor_property('mesh_type_to_import',
            unreal.FBXImportType.FBXIT_SKELETAL_MESH)

        options.skeletal_mesh_import_data.set_editor_property(
            'import_content_type', 
            unreal.FBXImportContentType.FBXICT_ALL
        )
        # set to import normals, otherwise Unreal will compute them
        # and it will take a long time, depending on the size of the mesh
        options.skeletal_mesh_import_data.set_editor_property(
            'normal_import_method', 
            unreal.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
        )

        task.options = options
        unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])  # noqa: E501

        # Create Asset Container
        lib.create_avalon_container(
            container=avalon_asset_name, path=asset_dir)

        namespace = asset_dir

        data = {
            "schema": "avalon-core:container-2.0",
            "id": pipeline.AVALON_CONTAINER_ID,
            "name": avalon_asset_name,
            "namespace": namespace,
            "asset_name": asset_name,
            "loader": str(self.__class__.__name__),
            "representation": context["representation"]["_id"],
            "parent": context["representation"]["parent"],
            "family": context["representation"]["context"]["family"]
        }
        unreal_pipeline.imprint(
            "{}/{}".format(asset_dir, avalon_asset_name), data)

        asset_content = unreal.EditorAssetLibrary.list_assets(
            asset_dir, recursive=True, include_folder=True
        )

        for a in asset_content:
            unreal.EditorAssetLibrary.save_asset(a)

        return asset_content

    def update(self, container, representation):
        node = container["objectName"]
        source_path = api.get_representation_path(representation)
        destination_path = container["namespace"]

        task = unreal.AssetImportTask()

        task.set_editor_property('filename', source_path)
        task.set_editor_property('destination_path', destination_path)
        # strip suffix
        task.set_editor_property('destination_name', node[:-4])
        task.set_editor_property('replace_existing', True)
        task.set_editor_property('automated', True)
        task.set_editor_property('save', True)

        task.options = unreal.FbxImportUI()
        task.options.set_editor_property('create_physics_asset', False)
        task.options.set_editor_property('import_as_skeletal', True)
        task.options.set_editor_property('import_animations', False)

        task.options.skeletal_mesh_import_data.set_editor_property(
            'normal_import_method', 
            unreal.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
        )

        # do import fbx and replace existing data
        unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
        container_path = "{}/{}".format(container["namespace"],
                                        container["objectName"])
        # update metadata
        unreal_pipeline.imprint(
            container_path, {"_id": str(representation["_id"])})

    def remove(self, container):
        unreal.EditorAssetLibrary.delete_directory(container["namespace"])
