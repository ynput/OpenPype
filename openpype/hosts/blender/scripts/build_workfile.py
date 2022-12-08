import os
import bpy

from openpype.client import (
    get_asset_by_name,
    get_subset_by_name,
    get_last_version_by_subset_id,
    get_representations,
)
from openpype.modules import ModulesManager
from openpype.pipeline import (
    legacy_io,
    legacy_create,
    discover_loader_plugins,
    load_container,
    loaders_from_representation,
)
from openpype.pipeline.create import get_legacy_creator_by_name


def load_subset(
    project_name, asset_name, subset_name, loader_type=None, ext="blend"
):
    """Load the representation of the last version of subset.

    Args:
        project_name (str): The project name.
        asset_name (str): The asset name.
        subset_name (str): The subset name.
        loader_type (str, optional): The loader name. Defaults to None.
        ext (str, optional): The representation extension. Defaults to "blend".

    Returns:
        The return of the `load_container()` function.
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

    all_loaders = discover_loader_plugins(project_name=project_name)
    loaders = loaders_from_representation(all_loaders, representation)
    for loader in loaders:
        if loader_type and loader_type not in loader.__name__:
            continue
        return load_container(loader, representation)


def create_instance(creator_name, instance_name, **options):
    """Create openpype publishable instance."""
    legacy_create(
        get_legacy_creator_by_name(creator_name),
        name=instance_name,
        asset=legacy_io.Session.get("AVALON_ASSET"),
        options=options,
    )


def load_casting(project_name, shot_name):
    """Load casting from shot_name using kitsu api."""

    modules_manager = ModulesManager()
    kitsu_module = modules_manager.modules_by_name.get("kitsu")
    if not kitsu_module or not kitsu_module.enabled:
        return

    import gazu

    gazu.client.set_host(os.environ["KITSU_SERVER"])
    gazu.log_in(os.environ["KITSU_LOGIN"], os.environ["KITSU_PWD"])

    shot_data = get_asset_by_name(project_name, shot_name, fields=["data"])

    shot = gazu.shot.get_shot(shot_data["data"]["zou"]["id"])
    casting = gazu.casting.get_shot_casting(shot)

    for actor in casting:
        for _ in range(actor["nb_occurences"]):
            if actor["asset_type_name"] == "Environment":
                subset_name = "setdressMain"
            else:
                subset_name = "rigMain"
            load_subset(project_name, actor["asset_name"], subset_name, "Link")

    gazu.log_out()


def build_model(asset_name):
    """Build model workfile.

    Args:
        asset_name (str): The current asset name from OpenPype Session.
    """
    bpy.ops.mesh.primitive_cube_add()
    bpy.context.object.name = f"{asset_name}_model"
    bpy.context.object.data.name = f"{asset_name}_model"
    create_instance("CreateModel", "modelMain", useSelection=True)


def build_look(project_name, asset_name):
    """Build look workfile.

    Args:
        project_name (str):  The current project name from OpenPype Session.
        asset_name (str):  The current asset name from OpenPype Session.
    """
    create_instance("CreateLook", "lookMain")
    load_subset(project_name, asset_name, "modelMain", "Append")


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
    load_subset(project_name, asset_name, "modelMain", "Append")


def build_layout(project_name, asset_name):
    """Build layout workfile.

    Args:
        project_name (str):  The current project name from OpenPype Session.
        asset_name (str):  The current asset name from OpenPype Session.
    """

    create_instance("CreateLayout", "layoutMain")

    # Load casting from kitsu breakdown.
    try:
        load_casting(project_name, asset_name)
    except RuntimeError:
        pass

    # Try using camera from loaded casting for the creation of
    # the instance camera collection.
    bpy.ops.object.select_all(action="DESELECT")
    for obj in bpy.context.scene.objects:
        if obj.type == "CAMERA":
            obj.select_set(True)
            break
    create_instance("CreateCamera", "cameraMain", useSelection=True)

    # Select camera from cameraMain instance to link with the review.
    bpy.ops.object.select_all(action="DESELECT")
    for obj in bpy.context.scene.objects:
        if obj.type == "CAMERA":
            obj.select_set(True)
            break
    create_instance("CreateReview", "reviewMain", useSelection=True)

    # load the board mov as image background linked into the camera.
    # TODO when fixed
    # load_subset(project_name, asset_name, "BoardReview", "Background", "mov")


def build_anim(project_name, asset_name):
    """Build anim workfile.

    Args:
        project_name (str):  The current project name from OpenPype Session.
        asset_name (str):  The current asset name from OpenPype Session.
    """

    load_subset(project_name, asset_name, "layoutMain", "Append")
    load_subset(project_name, asset_name, "cameraMain", "Link")

    # Select camera from cameraMain instance to link with the review.
    bpy.ops.object.select_all(action="DESELECT")
    for obj in bpy.context.scene.objects:
        if obj.type == "CAMERA":
            obj.select_set(True)
            break
    create_instance("CreateReview", "reviewMain", useSelection=True)


def build_render(project_name, asset_name):
    """Build render workfile.

    Args:
        project_name (str):  The current project name from OpenPype Session.
        asset_name (str):  The current asset name from OpenPype Session.
    """

    if not load_subset(project_name, asset_name, "layoutFromAnim", "Link"):
        load_subset(project_name, asset_name, "layoutMain", "Append")
    if not load_subset(project_name, asset_name, "cameraFromAnim", "Link"):
        load_subset(project_name, asset_name, "cameraMain", "Link")
    load_subset(project_name, asset_name, "animationMain", "Link")


def build_workfile():
    """build first workfile Main function."""
    project_name = legacy_io.Session["AVALON_PROJECT"]
    asset_name = legacy_io.Session.get("AVALON_ASSET")
    task_name = legacy_io.Session.get("AVALON_TASK").lower()

    if task_name in ("model", "modeling", "fabrication"):
        build_model(asset_name)

    elif task_name in ("texture", "look", "lookdev", "shader"):
        build_look(project_name, asset_name)

    elif task_name in ("rig", "rigging"):
        build_rig(project_name, asset_name)

    elif task_name == "layout":
        build_layout(project_name, asset_name)

    elif task_name in ("anim", "animation"):
        build_anim(project_name, asset_name)

    elif task_name in ("lighting", "light", "render", "rendering"):
        build_render(project_name, asset_name)

    else:
        return False

    return True


if __name__ == "__main__":
    build_workfile()
