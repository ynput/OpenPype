from maya import cmds, mel

import pyblish.api

from openpype.client import get_subset_by_name
from openpype.pipeline import KnownPublishError
from openpype.hosts.maya.api import lib


class CollectReview(pyblish.api.InstancePlugin):
    """Collect Review data

    """

    order = pyblish.api.CollectorOrder + 0.3
    label = 'Collect Review Data'
    families = ["review"]

    def process(self, instance):

        # Get panel.
        instance.data["panel"] = cmds.playblast(
            activeEditor=True
        ).rsplit("|", 1)[-1]

        # get cameras
        members = instance.data['setMembers']
        self.log.debug('members: {}'.format(members))
        cameras = cmds.ls(members, long=True, dag=True, cameras=True)
        camera = cameras[0] if cameras else None

        context = instance.context
        objectset = {
            i.data.get("instance_node") for i in context
        }

        # Collect display lights.
        display_lights = instance.data.get("displayLights", "default")
        if display_lights == "project_settings":
            settings = instance.context.data["project_settings"]
            settings = settings["maya"]["publish"]["ExtractPlayblast"]
            settings = settings["capture_preset"]["Viewport Options"]
            display_lights = settings["displayLights"]

        # Collect camera focal length.
        burninDataMembers = instance.data.get("burninDataMembers", {})
        if camera is not None:
            attr = camera + ".focalLength"
            if lib.get_attribute_input(attr):
                start = instance.data["frameStart"]
                end = instance.data["frameEnd"] + 1
                time_range = range(int(start), int(end))
                focal_length = [cmds.getAttr(attr, time=t) for t in time_range]
            else:
                focal_length = cmds.getAttr(attr)

            burninDataMembers["focalLength"] = focal_length

        # Account for nested instances like model.
        reviewable_subsets = list(set(members) & objectset)
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

            data["cameras"] = cameras
            data['review_camera'] = camera
            data['frameStartFtrack'] = instance.data["frameStartHandle"]
            data['frameEndFtrack'] = instance.data["frameEndHandle"]
            data['frameStartHandle'] = instance.data["frameStartHandle"]
            data['frameEndHandle'] = instance.data["frameEndHandle"]
            data['handleStart'] = instance.data["handleStart"]
            data['handleEnd'] = instance.data["handleEnd"]
            data["frameStart"] = instance.data["frameStart"]
            data["frameEnd"] = instance.data["frameEnd"]
            data['step'] = instance.data['step']
            # this (with other time related data) should be set on
            # representations. Once plugins like Extract Review start
            # using representations, this should be removed from here
            # as Extract Playblast is already adding fps to representation.
            data['fps'] = context.data['fps']
            data['review_width'] = instance.data['review_width']
            data['review_height'] = instance.data['review_height']
            data["isolate"] = instance.data["isolate"]
            data["panZoom"] = instance.data.get("panZoom", False)
            data["panel"] = instance.data["panel"]
            data["displayLights"] = display_lights
            data["burninDataMembers"] = burninDataMembers

            for key, value in instance.data["publish_attributes"].items():
                data["publish_attributes"][key] = value

            # The review instance must be active
            cmds.setAttr(str(instance) + '.active', 1)

            instance.data['remove'] = True

        else:
            project_name = instance.context.data["projectName"]
            asset_doc = instance.context.data['assetEntity']
            task = instance.context.data["task"]
            legacy_subset_name = task + 'Review'
            subset_doc = get_subset_by_name(
                project_name,
                legacy_subset_name,
                asset_doc["_id"],
                fields=["_id"]
            )
            if subset_doc:
                self.log.debug("Existing subsets found, keep legacy name.")
                instance.data['subset'] = legacy_subset_name

            instance.data["cameras"] = cameras
            instance.data['review_camera'] = camera
            instance.data['frameStartFtrack'] = \
                instance.data["frameStartHandle"]
            instance.data['frameEndFtrack'] = \
                instance.data["frameEndHandle"]
            instance.data["displayLights"] = display_lights
            instance.data["burninDataMembers"] = burninDataMembers
            # this (with other time related data) should be set on
            # representations. Once plugins like Extract Review start
            # using representations, this should be removed from here
            # as Extract Playblast is already adding fps to representation.
            instance.data["fps"] = instance.context.data["fps"]

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
