import os
from time import sleep, time
from typing import List, Set, Tuple
import bpy

from openpype.client import (
    get_asset_by_name,
    get_subset_by_name,
    get_last_version_by_subset_id,
    get_representations,
)
from openpype.client.entity_links import get_linked_representation_id
from openpype.client.entities import (
    get_representation_by_name,
    get_representation_by_id,
    get_version_by_id,
)
from openpype.hosts.blender.api.properties import OpenpypeContainer
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


def get_loader(project_name, representation, loader_type=None):
    """Get loader from representation by matching type.

    Args:
        project_name (str): The project name.
        representation (dict): The representation.
        loader_type (str, optional): The loader name. Defaults to None.

    Returns:
        The matched loader class.
    """
    all_loaders = discover_loader_plugins(project_name=project_name)
    loaders = loaders_from_representation(all_loaders, representation)
    for loader in loaders:
        if loader_type in loader.__name__:
            return loader


def download_subset(
    project_name, asset_name, subset_name, ext="blend"
) -> dict:
    """Download the representation of the subset last version on current site.

    Args:
        project_name (str): The project name.
        asset_name (str): The asset name.
        subset_name (str): The subset name.
        ext (str, optional): The representation extension. Defaults to "blend".

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

    last_version = get_last_version_by_subset_id(
        project_name,
        subset["_id"],
        fields=["_id"],
    )
    if not last_version:
        return

    representation = next(
        get_representations(
            project_name,
            version_ids=[last_version["_id"]],
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
    project_name, representation, loader_type=None
) -> Tuple[OpenpypeContainer, Set[bpy.types.ID]]:
    """Load the representation of the subset last version.

    Args:
        project_name (str): The project name.
        representation (dict): The representation.
        loader_type (str, optional): The loader name. Defaults to None.

    Returns:
        Tuple[OpenpypeContainer, Set[bpy.types.ID]]:
            (Container, Datablocks)
    """

    all_loaders = discover_loader_plugins(project_name=project_name)
    loaders = loaders_from_representation(all_loaders, representation)
    for loader in loaders:
        if loader_type in loader.__name__:
            return load_container(loader, representation)


def download_and_load_subset(
    project_name, asset_name, subset_name, loader_type=None
) -> Tuple[OpenpypeContainer, Set[bpy.types.ID]]:
    """Download and load the representation of the subset last version.

    Args:
        project_name (str): The project name.
        asset_name (str): The asset name.
        subset_name (str): The subset name.
        loader_type (str, optional): The loader name. Defaults to None.

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
        project_name: str, shot_name: str, asset_types: List[str] = None,
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
            if (
                actor["asset_type_name"] == "Character"
                and (not asset_types or "Character" in asset_types)
            ):
                subset_name = "rigMain"
            elif (
                actor["asset_type_name"] == "Environment"
                and (not asset_types or "Environment" in asset_types)
            ):
                subset_name = "setdressMain"
            else:
                continue

            # Download subset
            representation = download_subset(
                project_name, actor["asset_name"], subset_name
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
    for representation in representations:
        try:
            container, _datablocks = load_subset(
                project_name,
                representation,
                f"Link{representation['context']['family'].capitalize()}Loader",
            )
            containers.append(container)
        except TypeError:
            print(
                f"Cannot load {representation['context']['asset']} {representation['context']['subset']}."
            )

    return containers


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
        project_name, asset_name, "ConceptReference", "Reference", "jpg"
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
    for obj in bpy.context.scene.collection.all_objects:
        if obj.name.startswith("GDEFORM"):
            gdeformer_col.objects.link(obj)

        # Assign collection to sol(s) object(s)
        if obj.name.startswith("sol"):
            if obj.modifiers.get("GroundDeform"):
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
    concept_repre = download_subset(
        project_name, asset_name, "ConceptReference", "jpg"
    )

    # Create layout instance
    layout_instance = create_instance("CreateLayout", "layoutMain")

    # Load casting from kitsu breakdown.
    try:
        load_casting(project_name, asset_name)
        # NOTE load_casting runs wait_for_download

        # NOTE cannot rely on containers from load_casting, memory is shuffled
        containers = bpy.context.scene.openpype_containers

        # Link loaded containers to layout collection
        for c in containers:
            layout_instance.datablock_refs[0].datablock.children.link(
                c.outliner_entity
            )
            bpy.context.scene.collection.children.unlink(c.outliner_entity)

        # Create GDEFORMER collection
        create_gdeformer_collection(
            layout_instance.datablock_refs[0].datablock
        )
    except RuntimeError:
        containers = {}

        # Wait for download
        wait_for_download(
            project_name, [board_repre, audio_repre, concept_repre]
        )

    # Try to load camera from environment's setdress
    camera_collection = None
    env_asset_name = None
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
            # Load camera published at environment task
            cam_container, _cam_datablocks = download_and_load_subset(
                project_name,
                env_asset_name,
                "cameraMain",
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
    except RuntimeError:
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

    # load the board mov as image background linked into the camera
    load_subset(project_name, board_repre, "Background")

    # Delete sound sequence from board mov
    if len(bpy.context.scene.sequence_editor.sequences) > 0:
        sound_seq = bpy.context.scene.sequence_editor.sequences[-1]
        if sound_seq:
            bpy.context.scene.sequence_editor.sequences.remove(sound_seq)

    # load the audio reference as sound into sequencer
    load_subset(project_name, audio_repre, "Audio")

    # load the concept reference of the environment as image background.
    if env_asset_name:
        load_subset(
            project_name,
            concept_repre,
            "Background",
        )


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
    camera_repre = download_subset(project_name, asset_name, "cameraMain")
    wait_for_download(
        project_name,
        [workfile_layout_repre, layout_repre, board_repre, camera_repre],
    )

    # Load layout subset
    layout_container, _layout_datablocks = load_subset(
        project_name, layout_repre, "LinkLayoutLoader"
    )

    # Make container publishable, expose its content
    layout_collection_name = layout_container.outliner_entity.name
    bpy.ops.scene.make_container_publishable(
        container_name=layout_container.name
    )

    # Switch hero containers to versioned
    for container in bpy.context.scene.openpype_containers:
        container_metadata = container["avalon"]
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

        # Skip if current version representation is not hero
        if current_version["type"] != "hero_version":
            continue

        # Get last version representation
        last_version = get_last_version_by_subset_id(
            project_name, current_version["parent"], fields=["_id"]
        )
        version_representation = get_representation_by_name(
            project_name, "blend", last_version["_id"]
        )

        # Switch container to versioned
        loader = get_loader(
            project_name,
            version_representation,
            container_metadata.get("loader"),
        )
        switch_container(container_metadata, version_representation, loader)

    # Substitute overridden GDEFORMER collection by local one
    old_gdeform_collection = bpy.data.collections.get("GDEFORMER")
    if old_gdeform_collection:
        old_gdeform_collection.name += ".old"
        layout_collection = bpy.data.collections.get(layout_collection_name)
        create_gdeformer_collection(layout_collection)
        bpy.data.collections.remove(old_gdeform_collection)

    # Load camera
    cam_container, _cam_datablocks = load_subset(
        project_name, camera_repre, "AppendCameraLoader"
    )

    # Clean cam container from review collection
    # NOTE meant to be removed ASAP
    for i, d_ref in reversed(list(enumerate(cam_container.datablock_refs))):
        if isinstance(
            d_ref.datablock, bpy.types.Collection
        ) and d_ref.datablock.name.endswith("reviewMain"):
            bpy.data.collections.remove(d_ref.datablock)
            cam_container.datablock_refs.remove(i)

    # Make cam container publishable
    bpy.ops.scene.make_container_publishable(container_name=cam_container.name)
    cam_instance = bpy.context.scene.openpype_instances[-1]

    for obj in bpy.context.scene.objects:
        if obj.type == "ARMATURE":
            # Create animation instance
            variant_name = obj.name[obj.name.find("RIG_") + 4 :].capitalize()
            bpy.ops.scene.create_openpype_instance(
                creator_name="CreateAnimation",
                asset_name=asset_name,
                subset_name=f"animation{variant_name}",
                datapath="objects",
                datablock_name=obj.name,
                use_selection=False,
            )

    # Create review
    camera_collection = next(
        (
            d_ref.datablock
            for d_ref in cam_instance.datablock_refs
            if isinstance(d_ref.datablock, bpy.types.Collection)
        ),
        None,
    )
    bpy.ops.scene.create_openpype_instance(
        creator_name="CreateReview",
        asset_name=asset_name,
        subset_name="reviewMain",
        datapath="collections",
        datablock_name=camera_collection.name,
        use_selection=False,
    )

    # load the board mov as image background linked into the camera
    load_subset(project_name, board_repre, "Background")


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
