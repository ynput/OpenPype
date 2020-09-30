from avalon import api
from avalon import unreal as avalon_unreal
import unreal


class AnimationFBXLoader(api.Loader):
    """Load Unreal SkeletalMesh from FBX"""

    families = ["animation"]
    label = "Import FBX Animation"
    representations = ["fbx"]
    icon = "cube"
    color = "orange"

    def load(self, context, name, namespace, options = None):
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

        print("Loading animation")
        tools = unreal.AssetToolsHelpers().get_asset_tools()
        temp_dir, temp_name = tools.create_unique_asset_name(
            "/Game/{}".format(name), "_TMP"
        )

        unreal.EditorAssetLibrary.make_directory(temp_dir)

        asset = context.get('asset')
        asset_name = asset.get('name')

        destination_name = "{}_{}".format(asset_name, name)

        automated = False

        task = unreal.AssetImportTask()
        task.options = unreal.FbxImportUI()

        # If there are no options, the process cannot be automated
        if options:
            automated = True
            actor = unreal.EditorLevelLibrary.get_actor_reference(
                'PersistentLevel:' + options.get('instance_name'))
            skeleton = actor.skeletal_mesh_component.skeletal_mesh.skeleton
            task.options.set_editor_property('skeleton', skeleton)

        task.set_editor_property('filename', self.fname)
        task.set_editor_property('destination_path', temp_dir)
        task.set_editor_property('destination_name', destination_name)
        task.set_editor_property('replace_existing', True)
        task.set_editor_property('automated', automated)
        task.set_editor_property('save', True)

        # set import options here
        task.options.set_editor_property(
            'automated_import_should_detect_type', True)
        task.options.set_editor_property(
            'original_import_type', unreal.FBXImportType.FBXIT_ANIMATION)
        task.options.set_editor_property('import_mesh', False)
        task.options.set_editor_property('import_animations', True)

        task.options.skeletal_mesh_import_data.set_editor_property(
            'import_content_type', 
            unreal.FBXImportContentType.FBXICT_SKINNING_WEIGHTS
        )

        unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])

        imported_assets = unreal.EditorAssetLibrary.list_assets(
            temp_dir, recursive=True, include_folder=True
        )
        new_dir = avalon_unreal.containerise(
            name, namespace, imported_assets, context, self.__class__.__name__)

        asset_content = unreal.EditorAssetLibrary.list_assets(
            new_dir, recursive=True, include_folder=True
        )

        animation = None

        for a in asset_content:
            imported_asset_data = unreal.EditorAssetLibrary.find_asset_data(a)
            imported_asset = unreal.AssetRegistryHelpers.get_asset(
                imported_asset_data)
            if imported_asset.__class__ == unreal.AnimSequence:
                animation = imported_asset
                break

        if animation:
            animation.set_editor_property('enable_root_motion', True)
            actor.skeletal_mesh_component.set_editor_property(
                'animation_mode', unreal.AnimationMode.ANIMATION_SINGLE_NODE)
            actor.skeletal_mesh_component.animation_data.set_editor_property(
                'anim_to_play', animation)

        unreal.EditorAssetLibrary.delete_directory(temp_dir)

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
        avalon_unreal.imprint(
            container_path, {"_id": str(representation["_id"])})

    def remove(self, container):
        unreal.EditorAssetLibrary.delete_directory(container["namespace"])
