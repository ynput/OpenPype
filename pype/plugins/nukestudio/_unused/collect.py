from pyblish import api

class CollectFramerate(api.ContextPlugin):
    """Collect framerate from selected sequence."""

    order = api.CollectorOrder
    label = "Collect Framerate"
    hosts = ["nukestudio"]

    def process(self, context):
        for item in context.data.get("selection", []):
            context.data["framerate"] = item.sequence().framerate().toFloat()
            return


class CollectTrackItems(api.ContextPlugin):
    """Collect all tasks from submission."""

    order = api.CollectorOrder
    label = "Collect Track Items"
    hosts = ["nukestudio"]

    def process(self, context):
        import os

        submission = context.data.get("submission", None)
        data = {}

        # Set handles
        handles = 0
        if submission:
            for task in submission.getLeafTasks():

                if task._cutHandles:
                    handles = task._cutHandles
                    self.log.info("__ handles: '{}'".format(handles))

                # Skip audio track items
                media_type = "core.Hiero.Python.TrackItem.MediaType.kAudio"
                if str(task._item.mediaType()) == media_type:
                    continue

                item = task._item
                if item.name() not in data:
                    data[item.name()] = {"item": item, "tasks": [task]}
                else:
                    data[item.name()]["tasks"].append(task)

                data[item.name()]["startFrame"] = task.outputRange()[0]
                data[item.name()]["endFrame"] = task.outputRange()[1]
        else:
            for item in context.data.get("selection", []):
                # Skip audio track items
                # Try/Except is to handle items types, like EffectTrackItem
                try:
                    media_type = "core.Hiero.Python.TrackItem.MediaType.kVideo"
                    if str(item.mediaType()) != media_type:
                        continue
                except:
                    continue

                data[item.name()] = {
                    "item": item,
                    "tasks": [],
                    "startFrame": item.timelineIn(),
                    "endFrame": item.timelineOut()
                }

        for key, value in data.items():

            context.create_instance(
                name=key,
                subset="trackItem",
                asset=value["item"].name(),
                item=value["item"],
                family="trackItem",
                tasks=value["tasks"],
                startFrame=value["startFrame"] + handles,
                endFrame=value["endFrame"] - handles,
                handles=handles
            )
            context.create_instance(
                name=key + "_review",
                subset="reviewItem",
                asset=value["item"].name(),
                item=value["item"],
                family="trackItem_review",
                families=["output"],
                handles=handles,
                output_path=os.path.abspath(
                    os.path.join(
                        context.data["activeProject"].path(),
                        "..",
                        "workspace",
                        key + ".mov"
                    )
                )
            )


class CollectTasks(api.ContextPlugin):
    """Collect all tasks from submission."""

    order = api.CollectorOrder + 0.01
    label = "Collect Tasks"
    hosts = ["nukestudio"]

    def process(self, context):
        import os
        import re

        import hiero.exporters as he
        import clique

        for parent in context:
            if "trackItem" != parent.data["family"]:
                continue

            for task in parent.data["tasks"]:
                asset_type = None

                hiero_cls = he.FnSymLinkExporter.SymLinkExporter
                if isinstance(task, hiero_cls):
                    asset_type = "img"
                    movie_formats = [".mov", ".R3D"]
                    ext = os.path.splitext(task.resolvedExportPath())[1]
                    if ext in movie_formats:
                        asset_type = "mov"

                hiero_cls = he.FnTranscodeExporter.TranscodeExporter
                if isinstance(task, hiero_cls):
                    asset_type = "img"
                    if task.resolvedExportPath().endswith(".mov"):
                        asset_type = "mov"

                hiero_cls = he.FnNukeShotExporter.NukeShotExporter
                if isinstance(task, hiero_cls):
                    asset_type = "scene"

                hiero_cls = he.FnAudioExportTask.AudioExportTask
                if isinstance(task, hiero_cls):
                    asset_type = "audio"

                # Skip all non supported export types
                if not asset_type:
                    continue

                resolved_path = task.resolvedExportPath()

                # Formatting the basename to not include frame padding or
                # extension.
                name = os.path.splitext(os.path.basename(resolved_path))[0]
                name = name.replace(".", "")
                name = name.replace("#", "")
                name = re.sub(r"%.*d", "", name)
                instance = context.create_instance(name=name, parent=parent)

                instance.data["task"] = task
                instance.data["item"] = parent.data["item"]

                instance.data["family"] = "trackItem.task"
                instance.data["families"] = [asset_type, "local", "task"]

                label = "{1}/{0} - {2} - local".format(
                    name, parent, asset_type
                )
                instance.data["label"] = label

                instance.data["handles"] = parent.data["handles"]

                # Add collection or output
                if asset_type == "img":
                    collection = None

                    if "#" in resolved_path:
                        head = resolved_path.split("#")[0]
                        padding = resolved_path.count("#")
                        tail = resolved_path.split("#")[-1]

                        collection = clique.Collection(
                            head=head, padding=padding, tail=tail
                        )

                    if "%" in resolved_path:
                        collection = clique.parse(
                            resolved_path, pattern="{head}{padding}{tail}"
                        )

                    instance.data["collection"] = collection
                else:
                    instance.data["output_path"] = resolved_path
