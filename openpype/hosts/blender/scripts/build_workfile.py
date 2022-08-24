import os
import bpy


from openpype.client import (
    get_last_version_by_subset_name,
    get_representations,
)
from openpype.lib import get_creator_by_name
from openpype.modules import ModulesManager
from openpype.pipeline import (
    legacy_io,
    legacy_create,

    discover_loader_plugins,
    load_container,
    loaders_from_representation,
)


ALL_LOADERS = discover_loader_plugins()
PROJET_NAME = legacy_io.Session["AVALON_PROJECT"]


def load_subset(asset_name, subset_name, loader_type=None):
    last_version = get_last_version_by_subset_name(
        PROJET_NAME,
        subset_name,
        asset_name=asset_name,
        fields=["_id"],
    )
    if not last_version:
        return

    repre_blend = next(
        get_representations(
            PROJET_NAME,
            version_ids=[last_version["_id"]],
            extensions=["blend"],
        ),
        None
    )
    if not repre_blend:
        return

    loaders = loaders_from_representation(ALL_LOADERS, repre_blend)
    for loader in loaders:
        if loader_type and loader_type not in loader.__name__:
            continue
        return load_container(loader, repre_blend)


def create_instance(creator_name, instance_name):
    legacy_create(
        get_creator_by_name(creator_name),
        name=instance_name,
        asset=legacy_io.Session.get("AVALON_ASSET"),
    )


def load_casting(shot_name):

    modules_manager = ModulesManager()
    kitsu_module = modules_manager.modules_by_name.get("kitsu")
    if not kitsu_module or not kitsu_module.enabled:
        return

    import gazu

    gazu.client.set_host(os.environ["KITSU_SERVER"])
    gazu.log_in(os.environ["KITSU_LOGIN"], os.environ["KITSU_PWD"])

    project = gazu.project.get_project_by_name(PROJET_NAME)
    episode = gazu.shot.get_episode_by_name(project, "E01")
    sequence = gazu.shot.get_sequence_by_name(project, "SQ01", episode=episode)
    shot = gazu.shot.get_shot_by_name(sequence, shot_name)
    casting = gazu.casting.get_shot_casting(shot)

    for actor in casting:
        for i in range(actor["nb_occurences"]):
            load_subset(actor["asset_name"], "rigMain", loader_type="Link")

    gazu.log_out()


def build_workfile():
    task_name = legacy_io.Session.get("AVALON_TASK").lower()
    asset_name = legacy_io.Session.get("AVALON_ASSET")

    if task_name in ("model", "modeling"):
        create_instance("CreateModel", "modelMain")

    elif task_name in (
        "texture", "texturing", "look", "lookdev", "shader", "shadering"
    ):
        create_instance("CreateLook", "lookMain")
        load_subset(asset_name, "modelMain", loader_type="Append")

    elif task_name in ("rig", "rigging"):
        create_instance("CreateRig", "rigMain")
        load_subset(asset_name, "modelMain", loader_type="Append")

    elif task_name == "layout":
        create_instance("CreateLayout", "layoutMain")
        create_instance("CreateCamera", "cameraMain")
        # create_instance("CreateReview", "reviewMain")
        # load_casting(asset_name)

    elif task_name in ("anim", "animation"):
        load_subset(asset_name, "layoutMain", loader_type="Append")
        load_subset(asset_name, "cameraMain", loader_type="Link")
        # create_instance("CreateReview", "reviewMain")

    elif task_name in ("lighting", "light", "render", "rendering"):
        if not load_subset(asset_name, "layoutFromAnim", loader_type="Link"):
            load_subset(asset_name, "layoutMain", loader_type="Append")
        if not load_subset(asset_name, "cameraFromAnim", loader_type="Link"):
            load_subset(asset_name, "cameraMain", loader_type="Link")
        load_subset(asset_name, "animationMain", loader_type="Link")
    else:
        return False

    return True
