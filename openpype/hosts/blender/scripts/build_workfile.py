import os
from time import sleep, time
from typing import List, Set, Tuple
import bpy

from openpype.client import (
    get_asset_by_name,
    get_subset_by_name,
    get_last_version_by_subset_id,
    get_hero_version_by_subset_id,
    get_representations,
)
from openpype.client.entity_links import get_linked_representation_id
from openpype.client.entities import (
    get_representation_by_name,
    get_representation_by_id,
    get_version_by_id,
)
from openpype.hosts.blender.api.properties import OpenpypeContainer
from openpype.hosts.blender.api.lib import (
    add_datablocks_to_container,
    update_scene_containers,
)
from openpype.hosts.blender.api.utils import BL_TYPE_DATAPATH
from openpype.lib.local_settings import get_local_site_id
from openpype.modules import ModulesManager
from openpype.pipeline import (
    legacy_io,
    legacy_create,
    discover_loader_plugins,
    load_container,
    loaders_from_representation,
)
from openpype.pipeline.create import get_legacy_creator_by_name
from openpype.pipeline.load.utils import switch_container


def get_loader(project_name: str, representation: dict, loader_type: str):
    """Get loader from representation by matching type.

    Args:
        project_name (str): The project name.
        representation (dict): The representation.
        loader_type (str): The loader name.

    Returns:
        The matched loader class.
    """
    all_loaders = discover_loader_plugins(project_name=project_name)
    loaders = loaders_from_representation(all_loaders, representation)
    for loader in loaders:
        if loader_type in loader.__name__:
            return loader


def download_subset(
    project_name, asset_name, subset_name, ext="blend", hero=False
) -> dict:
    """Download the representation of the subset last version on current site.

    Args:
        project_name (str): The project name.
        asset_name (str): The asset name.
        subset_name (str): The subset name.
        ext (str, optional): The representation extension. Defaults to "blend".
        hero (bool, optional): Use hero version.

    Returns:
        dict: The subset representation.
    """
    asset = get_asset_by_name(project_name, asset_name, fields=["_id"])
    if not asset:
        return

    subset = get_subset_by_name(
        project_name,
        subset_name,
        asset["_id"],
        fields=["_id"],
    )
    if not subset:
        return

    version = None
    if hero:
        version = get_hero_version_by_subset_id(
            project_name,
            subset["_id"],
            fields=["_id"],
        )
    if not version:
        version = get_last_version_by_subset_id(
            project_name,
            subset["_id"],
            fields=["_id"],
        )
    if not version:
        return

    representation = next(
        get_representations(
            project_name,
            version_ids=[version["_id"]],
            context_filters={"ext": [ext]},
        ),
        None,
    )
    if not representation:
        return

    # Get sync server
    modules_manager = ModulesManager()
    sync_server = modules_manager.get("sync_server")
    local_site_id = get_local_site_id()

    # Add linked representations
    representation_ids = {representation["_id"]}
    representation_ids.update(
        get_linked_representation_id(
            project_name, repre_id=representation["_id"]
        )
    )

    # Add local site to representations
    for repre_id in representation_ids:
        # Check if representation is already on site
        if not sync_server.is_representation_on_site(
            project_name, repre_id, local_site_id
        ):
            sync_server.add_site(
                project_name,
                repre_id,
                local_site_id,
                priority=99,
                force=True,
            )

    return representation


def wait_for_download(project_name, representations: List[dict]):
    """Wait for download of representations.

    Args:
        project_name (str): Project name.
        representations (List[dict]): List of representations to wait for.
    """
    # Get sync server
    modules_manager = ModulesManager()
    sync_server = modules_manager.get("sync_server")

    # Reset timer
    sync_server.reset_timer()

    # Wait for download
    local_site_id = get_local_site_id()
    start = time()  # 5 minutes timeout
    while (
        not all(
            sync_server.is_representation_on_site(
                project_name, r["_id"], local_site_id
            )
            for r in representations
            if r
        )
        and time() - start < 300
    ):
        sleep(5)


def load_subset(
    project_name: str, representation: dict, loader_type: str
) -> Tuple[OpenpypeContainer, Set[bpy.types.ID]]:
    """Load the representation of the subset last version.

    Args:
        project_name (str): The project name.
        representation (dict): The representation.
        loader_type (str): The loader name.

    Returns:
        Tuple[OpenpypeContainer, Set[bpy.types.ID]]:
            (Container, Datablocks)
    """

    all_loaders = discover_loader_plugins(project_name=project_name)
    loaders = loaders_from_representation(all_loaders, representation)
    for loader in reversed(loaders):
        if loader_type in loader.__name__:
            return load_container(loader, representation)


def download_and_load_subset(
    project_name: str, asset_name: str, subset_name: str, loader_type: str
) -> Tuple[OpenpypeContainer, Set[bpy.types.ID]]:
    """Download and load the representation of the subset last version.

    Args:
        project_name (str): The project name.
        asset_name (str): The asset name.
        subset_name (str): The subset name.
        loader_type (str): The loader name.

    Returns:
        Tuple[OpenpypeContainer, Set[bpy.types.ID]]:
            (Container, Datablocks)
    """
    representation = download_subset(project_name, asset_name, subset_name)
    wait_for_download(project_name, [representation])
    return load_subset(project_name, representation, loader_type)


def create_instance(creator_name, instance_name, **options):
    """Create openpype publishable instance."""
    return legacy_create(
        get_legacy_creator_by_name(creator_name),
        name=instance_name,
        asset=legacy_io.Session.get("AVALON_ASSET"),
        options=options,
    )


def download_kitsu_casting(
    project_name: str,
    shot_name: str,
    asset_types: List[str] = None,
) -> List[dict]:
    """Download kitsu casting

    Args:
        project_name (str): Current project name from OpenPype Session.
        shot_name (str): Current shot name from OpenPype Session.
        asset_types (List[str]): Asset types to include.
            All supported asset types if none provided. Defaults to None.

    Returns:
        list: Representations.
    """

    # Check if kitsu_module is available
    kitsu_module = ModulesManager().modules_by_name.get("kitsu")
    assert kitsu_module and kitsu_module.enabled, "Kitsu module is unavailable"

    import gazu

    # Connect to gazu
    gazu.client.set_host(os.environ["KITSU_SERVER"])
    gazu.log_in(os.environ["KITSU_LOGIN"], os.environ["KITSU_PWD"])

    # Get casting
    casting = gazu.casting.get_shot_casting(
        gazu.shot.get_shot(
            get_asset_by_name(project_name, shot_name, fields=["data"])[
                "data"
            ]["zou"]["id"]
        )
    )

    # Logout from gazu
    gazu.log_out()

    representations = []
    for actor in casting:
        for _ in range(actor["nb_occurences"]):
            if actor["asset_type_name"] == "Environment" and (
                not asset_types or "Environment" in asset_types
            ):
                subset_name = "setdressMain"
            elif not asset_types or actor["asset_type_name"] in asset_types:
                subset_name = "rigMain"
            else:
                continue

            # Download subset
            representation = download_subset(
                project_name, actor["asset_name"], subset_name, hero=True
            )
            if not representation and actor["asset_type_name"] in (
                "Bidulo",
                "Props",
            ):
                representation = download_subset(
                    project_name, actor["asset_name"], "modelMain"
                )
            if representation:
                representations.append(representation)

    wait_for_download(project_name, representations)

    return representations


def load_casting(project_name: str, shot_name: str) -> Set[OpenpypeContainer]:
    """Load casting from shot_name using kitsu api.

     Args:
        project_name (str): Current project name from OpenPype Session.
        shot_name (str): Current shot name from OpenPype Session.

    Returns:
        Set[OpenpypeContainer]: Casted assets containers.
    """

    representations = download_kitsu_casting(project_name, shot_name)

    # Load downloaded subsets
    containers = []
    all_datablocks = set()
    for representation in representations:
        try:
            container, datablocks = load_subset(
                project_name,
                representation,
                "Link",
            )
            containers.append(container)
            all_datablocks.update(datablocks)
        except TypeError:
            print(
                f"Cannot load {representation['context']['asset']}"
                f"{representation['context']['subset']}."
            )

    return containers, all_datablocks


def load_references(
    project_name: str, asset_name: str, board_repre: dict, audio_repre: dict
) -> List[str]:
    """Load references for the asset.

    Args:
        project_name (str): The project name.
        asset_name (str): The asset name.
        board_repre (dict): The board representation.
        audio_repre (dict): The audio representation.

    Returns:
        List[str]: Errors.
    """
    errors = []

    # load the board mov as image background linked into the camera
    if board_repre:
        load_subset(project_name, board_repre, "Background")
    else:
        errors.append(
            "load subset BoardReference failed:"
            f" Missing subset for {asset_name}"
        )

    # Delete sound sequence from board mov
    if len(bpy.context.scene.sequence_editor.sequences) > 0:
        if sound_seq := bpy.context.scene.sequence_editor.sequences[-1]:
            bpy.context.scene.sequence_editor.sequences.remove(sound_seq)

    # load the audio reference as sound into sequencer
    if audio_repre:
        load_subset(project_name, audio_repre, "Audio")
    else:
        errors.append(
            "load subset AudioReference failed:"
            f" Missing subset for {asset_name}"
        )

    return errors


def build_model(project_name, asset_name):
    """Build model workfile.

    Args:
        project_name (str):  The current project name from OpenPype Session.
        asset_name (str): The current asset name from OpenPype Session.
    """
    bpy.ops.mesh.primitive_cube_add()
    bpy.context.object.name = f"{asset_name}_model"
    bpy.context.object.data.name = f"{asset_name}_model"
    create_instance("CreateModel", "modelMain", useSelection=True)
    # load the concept reference as image reference in the scene.
    download_and_load_subset(
        project_name, asset_name, "ConceptReference", "Reference"
    )


def build_look(project_name, asset_name):
    """Build look workfile.

    Args:
        project_name (str):  The current project name from OpenPype Session.
        asset_name (str):  The current asset name from OpenPype Session.
    """
    create_instance("CreateLook", "lookMain")
    download_and_load_subset(
        project_name, asset_name, "modelMain", "AppendModelLoader"
    )


def build_rig(project_name, asset_name):
    """Build rig workfile.

    Args:
        project_name (str):  The current project name from OpenPype Session.
        asset_name (str):  The current asset name from OpenPype Session.
    """
    bpy.ops.object.armature_add()
    bpy.context.object.name = f"{asset_name}_armature"
    bpy.context.object.data.name = f"{asset_name}_armature"
    create_instance("CreateRig", "rigMain", useSelection=True)
    download_and_load_subset(
        project_name, asset_name, "modelMain", "AppendModelLoader"
    )


def create_gdeformer_collection(parent_collection: bpy.types.Collection):
    """Create GDEFORMER collection under a parent collection.

    Args:
        parent_collection (bpy.types.Collection): Collection to create GDEFORMER col in
    """
    # Create GDEFORMER collection
    gdeformer_col = bpy.data.collections.new("GDEFORMER")
    parent_collection.children.link(gdeformer_col)
    for obj in bpy.context.scene.objects:
        if obj.name.startswith("GDEFORM"):
            gdeformer_col.objects.link(obj)

        # Assign collection to sol(s) object(s)
        if obj.name.lower().startswith("sol") and obj.modifiers.get(
            "GroundDeform"
        ):
            obj.modifiers["GroundDeform"]["Input_2"] = gdeformer_col


def build_layout(project_name, asset_name):
    """Build layout workfile.

    Args:
        project_name (str):  The current project name from OpenPype Session.
        asset_name (str):  The current asset name from OpenPype Session.
    """
    # Download not casting subsets
    board_repre = download_subset(
        project_name, asset_name, "BoardReference", "mov"
    )
    audio_repre = download_subset(
        project_name, asset_name, "AudioReference", "wav"
    )

    # Create layout instance
    layout_instance = create_instance("CreateLayout", "layoutMain")
    layout_collection = next(
        iter(layout_instance.get_root_datablocks(bpy.types.Collection)),
        None,
    )

    # Load casting from kitsu breakdown.
    containers = {}
    errors = []
    try:
        _casting_containers, casting_datablocks = load_casting(
            project_name, asset_name
        )
        # NOTE load_casting runs wait_for_download

        # NOTE cannot rely on containers from load_casting, memory is shuffled
        containers = bpy.context.scene.openpype_containers

        # Link loaded containers to layout collection
        for container in containers:
            for root in container.get_root_datablocks(bpy.types.Collection):
                if root not in layout_collection.children.values():
                    layout_collection.children.link(root)
                if root in bpy.context.scene.collection.children.values():
                    bpy.context.scene.collection.children.unlink(root)

        # Create GDEFORMER collection
        create_gdeformer_collection(bpy.context.scene.collection)
    except RuntimeError as err:
        errors.append(f"Load casting failed ! {err}")

    # Wait for download
    wait_for_download(project_name, [board_repre, audio_repre])

    # Try to load datablocks from environment's setdress
    camera_collection = None
    env_asset_name = None
    setdress_world = None
    concept_repre = None
    try:
        # Get env asset name
        env_asset_name = next(
            (
                c["avalon"]["asset_name"]
                for c in containers
                if c.get("avalon", {}).get("family") == "setdress"
            ),
            None,
        )
        if env_asset_name:
            # Download concept reference
            concept_repre = download_subset(
                project_name, env_asset_name, "ConceptReference", "jpg"
            )

            # Download camera published at environment task
            cam_repre = download_subset(
                project_name,
                env_asset_name,
                "cameraMain",
            )

            # Wait for download
            wait_for_download(project_name, [concept_repre, cam_repre])

            # Load camera
            cam_container, _cam_datablocks = load_subset(
                project_name,
                cam_repre,
                "AppendCameraLoader",
            )

            # Make cam container publishable
            bpy.ops.scene.make_container_publishable(
                container_name=cam_container.name,
                convert_to_current_asset=True,
            )

            # Keep camera collection
            camera_collection = (
                bpy.context.scene.openpype_instances[-1]
                .datablock_refs[0]
                .datablock
            )

            # Get world from setdress
            setdress_world = next(
                (
                    datablock
                    for datablock in casting_datablocks
                    if isinstance(datablock, bpy.types.World)
                ),
                None,
            )
    except RuntimeError as err:
        errors.append(f"Build setdress failed ! {err}")
        camera_collection = None

    # Ensure camera instance
    if not camera_collection:
        bpy.ops.scene.create_openpype_instance(
            creator_name="CreateCamera",
            asset_name=asset_name,
            subset_name="cameraMain",
            gather_into_collection=True,
        )
        camera_collection = (
            bpy.context.scene.openpype_instances[-1]
            .datablock_refs[0]
            .datablock
        )

    # Create review instance with camera collection
    bpy.ops.scene.create_openpype_instance(
        creator_name="CreateReview",
        asset_name=asset_name,
        subset_name="reviewMain",
        datapath="collections",
        datablock_name=camera_collection.name,
    )

    # Assign setdress or last loaded world
    bpy.context.scene.world = setdress_world or bpy.data.worlds[-1]

    # Load Audio and Board
    errors.extend(
        load_references(project_name, asset_name, board_repre, audio_repre)
    )

    # load the concept reference of the environment as image background.
    if env_asset_name and concept_repre:
        load_subset(
            project_name,
            concept_repre,
            "Background",
        )

    assert not errors, ";\n\n".join(errors)


def build_anim(project_name, asset_name):
    """Build anim workfile.

    Args:
        project_name (str):  The current project name from OpenPype Session.
        asset_name (str):  The current asset name from OpenPype Session.
    """
    # Download not casting subsets
    workfile_layout_repre = download_subset(
        project_name, asset_name, "workfileLayout"
    )
    layout_repre = download_subset(project_name, asset_name, "layoutMain")
    board_repre = download_subset(
        project_name, asset_name, "BoardReference", "mov"
    )
    audio_repre = download_subset(
        project_name, asset_name, "AudioReference", "wav"
    )
    camera_repre = download_subset(project_name, asset_name, "cameraMain")
    wait_for_download(
        project_name,
        [workfile_layout_repre, layout_repre, board_repre, camera_repre],
    )

    # Load layout subset
    layout_container, _layout_datablocks = load_subset(
        project_name, layout_repre, "AppendLayoutLoader"
    )

    # Make container publishable, expose its content
    bpy.ops.scene.make_container_publishable(
        container_name=layout_container.name
    )

    update_scene_containers()

    # Switch hero containers to versioned
    errors = []
    setdress_container = None
    for container in bpy.context.scene.openpype_containers:
        container_metadata = container["avalon"]
        family = container_metadata.get("family")

        if family not in {"rig", "model", "setdress"}:
            continue

        # hold SetDress container
        is_setdress = family == "setdress"
        if is_setdress and not setdress_container:
            setdress_container = container

        # Get version representation
        current_version = get_version_by_id(
            project_name,
            container_metadata.get("parent"),
            fields=["_id", "parent", "type"],
        )

        # If current_version is None retry with other methods.
        if not current_version:
            current_representation = get_representation_by_id(
                project_name,
                container_metadata.get("representation"),
                fields=["parent"],
            )
            current_version = get_version_by_id(
                project_name,
                current_representation["parent"],
                fields=["_id", "parent", "type"],
            )
            # current_version is None again, skip this container.
            if not current_version:
                continue

        version_id = current_version["_id"] if family == "setdress" else None

        # if current version representation is hero get last version
        if current_version["type"] == "hero_version":
            last_version = get_last_version_by_subset_id(
                project_name, current_version["parent"], fields=["_id"]
            )
            if last_version:
                version_id = last_version["_id"]

        if not version_id:
            continue

        version_representation = get_representation_by_name(
            project_name, "blend", version_id
        )

        # get loader
        if is_setdress:
            loader_name = "LinkWoollySetdressLoader"
        else:
            loader_name = container_metadata.get("loader")

        if not loader_name or not isinstance(loader_name, str):
            continue

        # Switch container to versioned
        if (
            current_version["_id"] != version_id
            or container_metadata.get("loader") != loader_name
            or is_setdress  # force reload to relink world datablock
        ):
            try:
                switch_container(
                    container_metadata,
                    version_representation,
                    get_loader(
                        project_name,
                        version_representation,
                        loader_name,
                    ),
                )
            except (RuntimeError, AssertionError) as err:
                errors.append(f"Switch failed for {container.name}: {err}")
                continue

    # Substitute overridden GDEFORMER collection by local one
    scene_collections_by_name = {
        c.name: c for c in bpy.context.scene.collection.children_recursive
    }
    if gdeform_collection := scene_collections_by_name.get("GDEFORMER"):
        gdeform_collection.name += ".old"
        bpy.data.collections.remove(gdeform_collection)
    create_gdeformer_collection(bpy.context.scene.collection)

    # Get world from setdress
    setdress_world = None
    if setdress_container:
        for world in setdress_container.get_datablocks(
            bpy.types.World,
            only_local=False,
        ):
            setdress_world = world

    # Assign setdress or last loaded world
    if setdress_world:
        bpy.context.scene.world = setdress_world
    else:
        errors.append("World from SetDress not found!")

    # Load camera
    try:
        cam_container, _cam_datablocks = load_subset(
            project_name, camera_repre, "AppendCameraLoader"
        )
    except (RuntimeError, AssertionError) as err:
        errors.append(f"Load Camera failed: {err}")

    # Clean cam container from review collection
    # NOTE meant to be removed ASAP
    for i, d_ref in reversed(list(enumerate(cam_container.datablock_refs))):
        if isinstance(
            d_ref.datablock, bpy.types.Collection
        ) and d_ref.datablock.name.endswith("reviewMain"):
            bpy.data.collections.remove(d_ref.datablock)
            cam_container.datablock_refs.remove(i)

    # Make cam container publishable
    if cam_container:
        bpy.ops.scene.make_container_publishable(
            container_name=cam_container.name
        )
        cam_instance = bpy.context.scene.openpype_instances[-1]

        if camera_collection := next(
            (
                d
                for d in cam_instance.get_root_outliner_datablocks()
                if isinstance(d, bpy.types.Collection)
            ),
            None,
        ):
            bpy.ops.scene.create_openpype_instance(
                creator_name="CreateReview",
                asset_name=asset_name,
                subset_name="reviewMain",
                datapath="collections",
                datablock_name=camera_collection.name,
                use_selection=False,
            )

    instances_to_create = {}
    for container in bpy.context.scene.openpype_containers:
        container_metadata = container["avalon"]
        variant_name = container_metadata.get("asset_name")
        family = container_metadata.get("family")
        container_datablocks = container.get_datablocks(bpy.types.Object)

        if family == "setdress":
            # For setdress container we gather only the root collection.
            instances_to_create[variant_name] = list(
                d
                for d in container.get_root_outliner_datablocks()
                if isinstance(d, bpy.types.Collection)
            )
        else:
            # Get rigs
            armature_objects = {
                o for o in container_datablocks if o.type == "ARMATURE"
            }
            # Get animated objects
            animated_objects = {
                o
                for o in container_datablocks
                if o.animation_data and o.animation_data.action
            }
            # Add new instance creation container had rigs or animated members.
            if armature_objects or animated_objects:
                instances_to_create[variant_name] = list(
                    armature_objects | animated_objects
                )

    # Create instances and add datablocks
    for variant_name, objects in instances_to_create.items():
        bpy.ops.scene.create_openpype_instance(
            creator_name="CreateAnimation",
            asset_name=asset_name,
            subset_name=f"animation{variant_name}",
            datapath=BL_TYPE_DATAPATH.get(type(objects[0])),
            datablock_name=objects[0].name,
            use_selection=False,
        )
        animation_instance = bpy.context.scene.openpype_instances[-1]
        add_datablocks_to_container(objects[1:], animation_instance)

        # Enabled instance for publishing if any member objects are animated.
        publish_enabled = False
        for obj in objects:
            if (
                isinstance(obj, bpy.types.Object)
                and obj.animation_data
                and obj.animation_data.action
            ):
                publish_enabled = True
                break
            elif isinstance(obj, bpy.types.Collection):
                objects.extend(obj.all_objects)
        animation_instance.publish = publish_enabled

    # Load Audio and Board
    errors.extend(
        load_references(project_name, asset_name, board_repre, audio_repre)
    )

    assert not errors, ";\n\n".join(errors)


def build_lipsync(project_name: str, shot_name: str):
    """Build lipsync workfile.

    Args:
        project_name (str):  Current project name from OpenPype Session.
        shot_name (str):  Current shot name from OpenPype Session.
    """

    representations = download_kitsu_casting(
        project_name, shot_name, asset_types=["Character"]
    )

    for representation in representations:
        if representation:
            load_subset(
                project_name,
                representation,
                "rigMain",
                "LinkRigLoader",
            )
        else:
            print(
                f"Can't load {representation['context']['asset']} {'rigMain'}."
            )


def build_render(project_name, asset_name):
    """Build render workfile.

    Args:
        project_name (str):  The current project name from OpenPype Session.
        asset_name (str):  The current asset name from OpenPype Session.
    """
    # Download subsets
    layout_repre = download_subset(project_name, asset_name, "layoutMain")
    camera_repre = download_subset(project_name, asset_name, "cameraMain")
    anim_repre = download_subset(project_name, asset_name, "animationMain")
    wait_for_download(project_name, [layout_repre, camera_repre, anim_repre])

    # Load subsets
    load_subset(project_name, layout_repre, "AppendLayoutLoader")
    load_subset(project_name, camera_repre, "LinkCameraLoader")

    # TODO : Because subset animationMain no longer be used,
    # we need to load all animation subsets from the asset.
    _anim_container, anim_datablocks = load_subset(
        project_name, anim_repre, "LinkAnimationLoader"
    )

    # Try to assign linked actions by parsing their name
    for action in anim_datablocks:
        users = action.get("users", {})
        for user_name in users:
            obj = bpy.context.scene.objects.get(user_name)
            if obj:
                # Ensure animation data
                if not obj.animation_data:
                    obj.animation_data_create()

                # Assign action
                obj.animation_data.action = action
            else:
                print(
                    f"Cannot match armature by name '{user_name}' "
                    f"for action: {action.name}"
                )
                continue


def build_workfile():
    """build first workfile Main function."""
    project_name = legacy_io.Session["AVALON_PROJECT"]
    asset_name = legacy_io.Session.get("AVALON_ASSET")
    task_name = legacy_io.Session.get("AVALON_TASK").lower()

    if task_name in ("model", "modeling", "fabrication"):
        build_model(project_name, asset_name)

    elif task_name in ("texture", "look", "lookdev", "shader"):
        build_look(project_name, asset_name)

    elif task_name in ("rig", "rigging"):
        build_rig(project_name, asset_name)

    elif task_name == "layout":
        build_layout(project_name, asset_name)

    elif task_name in ("anim", "animation"):
        build_anim(project_name, asset_name)

    elif task_name == "lipsync":
        build_lipsync(project_name, asset_name)

    elif task_name in ("lighting", "light", "render", "rendering"):
        build_render(project_name, asset_name)

    else:
        return False

    # Auto save
    if bpy.data.filepath:
        bpy.ops.wm.save_mainfile()

    return True


if __name__ == "__main__":
    build_workfile()
