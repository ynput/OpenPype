from ayon_api import get_folder_by_name, get_folder_by_path, get_folders
from maya import cmds  # noqa: F401

from openpype import AYON_SERVER_ENABLED
from openpype.client import get_assets
from openpype.hosts.maya.api import plugin
from openpype.lib import BoolDef, EnumDef
from openpype.pipeline import (
    Creator,
    get_current_asset_name,
    get_current_project_name
)
from openpype.pipeline.create import CreatorError


class CreateMultishotLayout(plugin.MayaCreator):
    """Create a multishot layout in the Maya scene.

    This creator will create a Camera Sequencer in the Maya scene based on
    the shots found under the specified folder. The shots will be added to
    the sequencer in the order of their clipIn and clipOut values. For each
    shot a Layout will be created.

    """
    identifier = "io.openpype.creators.maya.multishotlayout"
    label = "Multishot Layout"
    family = "layout"
    icon = "project-diagram"

    def get_pre_create_attr_defs(self):
        # Present artist with a list of parents of the current context
        # to choose from. This will be used to get the shots under the
        # selected folder to create the Camera Sequencer.

        """
        Todo: get this needs to be switched to get_folder_by_path
              once the fork to pure AYON is done.

        Warning: this will not work for projects where the asset name
                 is not unique across the project until the switch mentioned
                 above is done.
        """

        current_folder = get_folder_by_name(
            project_name=get_current_project_name(),
            folder_name=get_current_asset_name(),
        )

        items_with_label = [
            dict(label=p if p != current_folder["name"] else f"{p} (current)",
                 value=str(p))
            for p in current_folder["path"].split("/")
        ]

        items_with_label.insert(0,
            dict(label=f"{self.project_name} "
                          "(shots directly under the project)",
                 value=None))

        return [
            EnumDef("shotParent",
                    default=current_folder["name"],
                    label="Shot Parent Folder",
                    items=items_with_label,
                    ),
            BoolDef("groupLoadedAssets",
                    label="Group Loaded Assets",
                    tooltip="Enable this when you want to publish group of "
                            "loaded asset",
                    default=False)
        ]

    def create(self, subset_name, instance_data, pre_create_data):
        shots = self.get_related_shots(
            folder_path=pre_create_data["shotParent"]
        )
        if not shots:
            # There are no shot folders under the specified folder.
            # We are raising an error here but in the future we might
            # want to create a new shot folders by publishing the layouts
            # and shot defined in the sequencer. Sort of editorial publish
            # in side of Maya.
            raise CreatorError("No shots found under the specified folder.")

        # Get layout creator
        layout_creator_id = "io.openpype.creators.maya.layout"
        layout_creator: Creator = self.create_context.creators.get(
            layout_creator_id)

        # Get OpenPype style asset documents for the shots
        op_asset_docs = get_assets(
            self.project_name, [s["id"] for s in shots])
        for shot in shots:
            # we are setting shot name to be displayed in the sequencer to
            # `shot name (shot label)` if the label is set, otherwise just
            # `shot name`. So far, labels are used only when the name is set
            # with characters that are not allowed in the shot name.
            if not shot["active"]:
                continue

            shot_name = f"{shot['name']}%s" % (
                f" ({shot['label']})" if shot["label"] else "")
            cmds.shot(sst=shot["attrib"]["clipIn"],
                      set=shot["attrib"]["clipOut"],
                      shotName=shot_name)

            # Create layout instance by the layout creator
            layout_creator.create(
                subset_name=layout_creator.get_subset_name(
                    self.get_default_variant(),
                    self.create_context.get_current_task_name(),
                    next(
                        asset_doc for asset_doc in op_asset_docs
                        if asset_doc["_id"] == shot["id"]
                    ),
                    self.project_name),
                instance_data={
                    "asset": shot["name"],
                },
                pre_create_data={
                    "groupLoadedAssets": pre_create_data["groupLoadedAssets"]
                }
            )

    def get_related_shots(self, folder_path: str):
        """Get all shots related to the current asset.

        Get all folders of type Shot under specified folder.

        Args:
            folder_path (str): Path of the folder.

        Returns:
            list: List of dicts with folder data.

        """
        # if folder_path is None, project is selected as a root
        # and its name is used as a parent id
        parent_id = [self.project_name]
        if folder_path:
            current_folder = get_folder_by_path(
                project_name=self.project_name,
                folder_path=folder_path,
            )
            parent_id = [current_folder["id"]]

        # get all child folders of the current one
        child_folders = get_folders(
            project_name=self.project_name,
            parent_ids=parent_id,
            fields=[
                "attrib.clipIn", "attrib.clipOut",
                "attrib.frameStart", "attrib.frameEnd",
                "name", "label", "path", "folderType", "id"
            ]
        )
        return [f for f in child_folders if f["folderType"] == "Shot"]


# blast this creator if Ayon server is not enabled
if not AYON_SERVER_ENABLED:
    del CreateMultishotLayout
