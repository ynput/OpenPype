import os
import pyblish.api

from openpype.client import get_representations
from openpype.hosts.openrv.api.pipeline import gather_containers
from openpype.pipeline import (
    legacy_io
)


class CollectSessionAnnotations(pyblish.api.ContextPlugin):
    """Collect session Annotations
    """

    order = pyblish.api.CollectorOrder - 0.02
    label = "Collect Session Annotations"
    hosts = ["openrv"]
    family = "annotation"

    def process(self, context):
        """Inject collection of annotated frames"""
        import rv

        project_name = legacy_io.Session["AVALON_PROJECT"]
        source_groups = []
        all_nodes = gather_containers()
        for container in all_nodes:

            self.log.debug("Container {} with properties: {}".format(
                container, rv.commands.properties(container)
            ))
            prop_namespace = container + ".openpype.namespace"
            prop_representation = container + ".openpype.representation"
            data_prop_namespace = rv.commands.getStringProperty(prop_namespace)[0]
            data_prop_representation_id = rv.commands.getStringProperty(prop_representation)[0]

            representations = get_representations(project_name,
                                                  representation_ids=[data_prop_representation_id])
            first_repre = next(iter(representations))  # first representation
            repre_context = first_repre["context"]
            source_representation_project = repre_context["project"]["name"]
            source_representation_asset = repre_context["asset"]
            source_representation_task = repre_context["task"]["name"]
            source_representation_subset = repre_context["subset"]
            source_group = rv.commands.nodeGroup(container)
            print("SOURCE GROUP ", source_group)
            source_groups.append(source_group)
            rv.commands.setViewNode(source_group)
            rv.commands.redraw()

            marked_frames = rv.commands.markedFrames()
            annotated_frames = rv.extra_commands.findAnnotatedFrames()

            asset_folder, file = os.path.split(rv.commands.sessionFileName())

            for marked in marked_frames:
                print("MARKED ------------ ", container,  marked, source_group)

            for noted_frame in annotated_frames:
                print("NOTED ------- ", container, noted_frame, source_group)
                rv.commands.setFrame(int(noted_frame))
                rv.commands.redraw()

                instance = context.create_instance(name=str(container))
                item_name = "note_{}_{}".format(
                    data_prop_namespace, noted_frame
                )

                # annotation_representation = {
                #     "tags": ["review", "ftrackreview"],
                #     "name": "thumbnail",
                #     "ext": "jpg",
                #     "files": "frames_1001.jpg",
                #     "stagingDir": "X:\\projects\\Sync\\DaliesPrep\\work\\prepDaily",
                #     # "thumbnail": True,
                #     # "comment": "NEW COMMENT FROM UI"
                #     "frameStart": noted_frame,
                #     "frameEnd": noted_frame,
                #     "fps": "25",
                # }

                data = {
                    # "subset": source_representation_subset + "_review_{}".format(noted_frame),
                    "subset": "annotation_{}".format(str(noted_frame)),
                    "tags": ["review", "ftrackreview"],
                    "asset": source_representation_asset,
                    "task": source_representation_task,
                    "label": str(item_name),
                    "publish": True,
                    "review": True,
                    "family": "annotation",
                    # "setMembers": [""],
                    "asset_folder_path": str(asset_folder),
                    "annotated_frame": str(noted_frame),
                    "comment": "NEW COMMENT FROM UI {}".format(noted_frame),
                }

                instance.data.update(data)
                #
                # if "representations" not in instance.data:
                #     instance.data["representations"] = []
                #
                # instance.data["representations"].append(annotation_representation)

            view_node = rv.commands.viewNode()
            intent = context.data.get("intent")
