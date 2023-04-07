from maya import cmds, mel

import pyblish.api

from openpype.client import get_subset_by_name
from openpype.pipeline import legacy_io, KnownPublishError
from openpype.hosts.maya.api.lib import get_attribute_input


class CollectReview(pyblish.api.InstancePlugin):
    """Collect Review data

    """

    order = pyblish.api.CollectorOrder + 0.3
    label = 'Collect Review Data'
    families = ["review"]

    def process(self, instance):

        self.log.debug('instance: {}'.format(instance))

        task = legacy_io.Session["AVALON_TASK"]

        # Get panel.
        instance.data["panel"] = cmds.playblast(
            activeEditor=True
        ).split("|")[-1]

        # get cameras
        members = instance.data['setMembers']
        cameras = cmds.ls(members, long=True,
                          dag=True, cameras=True)
        self.log.debug('members: {}'.format(members))

        # validate required settings
        if len(cameras) == 0:
            raise KnownPublishError("No camera found in review "
                                    "instance: {}".format(instance))
        elif len(cameras) > 2:
            raise KnownPublishError(
                "Only a single camera is allowed for a review instance but "
                "more than one camera found in review instance: {}. "
                "Cameras found: {}".format(instance, ", ".join(cameras)))

        camera = cameras[0]
        self.log.debug('camera: {}'.format(camera))

        context = instance.context
        objectset = context.data['objectsets']

        reviewable_subsets = list(set(members) & set(objectset))
        if reviewable_subsets:
            if len(reviewable_subsets) > 1:
                raise KnownPublishError(
                    "Multiple attached subsets for review are not supported. "
                    "Attached: {}".format(", ".join(reviewable_subsets))
                )

            reviewable_subset = reviewable_subsets[0]
            self.log.debug(
                "Subset attached to review: {}".format(reviewable_subset)
            )

            # Find the relevant publishing instance in the current context
            reviewable_inst = next(inst for inst in context
                                   if inst.name == reviewable_subset)
            data = reviewable_inst.data

            self.log.debug(
                'Adding review family to {}'.format(reviewable_subset)
            )
            if data.get('families'):
                data['families'].append('review')
            else:
                data['families'] = ['review']

            data['review_camera'] = camera
            data['frameStartFtrack'] = instance.data["frameStartHandle"]
            data['frameEndFtrack'] = instance.data["frameEndHandle"]
            data['frameStartHandle'] = instance.data["frameStartHandle"]
            data['frameEndHandle'] = instance.data["frameEndHandle"]
            data["frameStart"] = instance.data["frameStart"]
            data["frameEnd"] = instance.data["frameEnd"]
            data['step'] = instance.data['step']
            data['fps'] = instance.data['fps']
            data['review_width'] = instance.data['review_width']
            data['review_height'] = instance.data['review_height']
            data["isolate"] = instance.data["isolate"]
            data["panZoom"] = instance.data.get("panZoom", False)
            data["panel"] = instance.data["panel"]

            # The review instance must be active
            cmds.setAttr(str(instance) + '.active', 1)

            instance.data['remove'] = True

        else:
            legacy_subset_name = task + 'Review'
            asset_doc = instance.context.data['assetEntity']
            project_name = legacy_io.active_project()
            subset_doc = get_subset_by_name(
                project_name,
                legacy_subset_name,
                asset_doc["_id"],
                fields=["_id"]
            )
            if subset_doc:
                self.log.debug("Existing subsets found, keep legacy name.")
                instance.data['subset'] = legacy_subset_name

            instance.data['review_camera'] = camera
            instance.data['frameStartFtrack'] = \
                instance.data["frameStartHandle"]
            instance.data['frameEndFtrack'] = \
                instance.data["frameEndHandle"]

            # make ftrack publishable
            instance.data.setdefault("families", []).append('ftrack')

            cmds.setAttr(str(instance) + '.active', 1)

            # Collect audio
            playback_slider = mel.eval('$tmpVar=$gPlayBackSlider')
            audio_name = cmds.timeControl(playback_slider,
                                          query=True,
                                          sound=True)
            display_sounds = cmds.timeControl(
                playback_slider, query=True, displaySound=True
            )

            def get_audio_node_data(node):
                return {
                    "offset": cmds.getAttr("{}.offset".format(node)),
                    "filename": cmds.getAttr("{}.filename".format(node))
                }

            audio_data = []

            if audio_name:
                audio_data.append(get_audio_node_data(audio_name))

            elif display_sounds:
                start_frame = int(cmds.playbackOptions(query=True, min=True))
                end_frame = int(cmds.playbackOptions(query=True, max=True))

                for node in cmds.ls(type="audio"):
                    # Check if frame range and audio range intersections,
                    # for whether to include this audio node or not.
                    duration = cmds.getAttr("{}.duration".format(node))
                    start_audio = cmds.getAttr("{}.offset".format(node))
                    end_audio = start_audio + duration

                    if start_audio <= end_frame and end_audio > start_frame:
                        audio_data.append(get_audio_node_data(node))

            instance.data["audio"] = audio_data

        # Collect focal length.
        attr = camera + ".focalLength"
        if get_attribute_input(attr):
            start = instance.data["frameStart"]
            end = instance.data["frameEnd"] + 1
            focal_length = [
                cmds.getAttr(attr, time=t) for t in range(int(start), int(end))
            ]
        else:
            focal_length = cmds.getAttr(attr)

        key = "focalLength"
        try:
            instance.data["burninDataMembers"][key] = focal_length
        except KeyError:
            instance.data["burninDataMembers"] = {key: focal_length}
