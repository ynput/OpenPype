from maya import cmds, mel
import pymel.core as pm

import pyblish.api

from openpype.pipeline import legacy_io


class CollectReview(pyblish.api.InstancePlugin):
    """Collect Review data

    """

    order = pyblish.api.CollectorOrder + 0.3
    label = 'Collect Review Data'
    families = ["review"]
    legacy = True

    def process(self, instance):

        self.log.debug('instance: {}'.format(instance))

        task = legacy_io.Session["AVALON_TASK"]

        # get cameras
        members = instance.data['setMembers']
        cameras = cmds.ls(members, long=True,
                          dag=True, cameras=True)
        self.log.debug('members: {}'.format(members))

        # validate required settings
        assert len(cameras) == 1, "Not a single camera found in extraction"
        camera = cameras[0]
        self.log.debug('camera: {}'.format(camera))

        objectset = instance.context.data['objectsets']

        reviewable_subset = None
        reviewable_subset = list(set(members) & set(objectset))
        if reviewable_subset:
            assert len(reviewable_subset) <= 1, "Multiple subsets for review"
            self.log.debug('subset for review: {}'.format(reviewable_subset))

            i = 0
            for inst in instance.context:

                self.log.debug('filtering {}'.format(inst))
                data = instance.context[i].data

                if inst.name != reviewable_subset[0]:
                    self.log.debug('subset name does not match {}'.format(
                        reviewable_subset[0]))
                    i += 1
                    continue

                if data.get('families'):
                    data['families'].append('review')
                else:
                    data['families'] = ['review']
                self.log.debug('adding review family to {}'.format(
                    reviewable_subset))
                data['review_camera'] = camera
                # data["publish"] = False
                data['frameStartFtrack'] = instance.data["frameStartHandle"]
                data['frameEndFtrack'] = instance.data["frameEndHandle"]
                data['frameStartHandle'] = instance.data["frameStartHandle"]
                data['frameEndHandle'] = instance.data["frameEndHandle"]
                data["frameStart"] = instance.data["frameStart"]
                data["frameEnd"] = instance.data["frameEnd"]
                data['handles'] = instance.data.get('handles', None)
                data['step'] = instance.data['step']
                data['fps'] = instance.data['fps']
                data["isolate"] = instance.data["isolate"]
                cmds.setAttr(str(instance) + '.active', 1)
                self.log.debug('data {}'.format(instance.context[i].data))
                instance.context[i].data.update(data)
                instance.data['remove'] = True
                self.log.debug('isntance data {}'.format(instance.data))
        else:
            if self.legacy:
                instance.data['subset'] = task + 'Review'
            else:
                subset = "{}{}{}".format(
                    task,
                    instance.data["subset"][0].upper(),
                    instance.data["subset"][1:]
                )
                instance.data['subset'] = subset

            instance.data['review_camera'] = camera
            instance.data['frameStartFtrack'] = \
                instance.data["frameStartHandle"]
            instance.data['frameEndFtrack'] = \
                instance.data["frameEndHandle"]

            # make ftrack publishable
            instance.data["families"] = ['ftrack']

            cmds.setAttr(str(instance) + '.active', 1)

            # Collect audio
            playback_slider = mel.eval('$tmpVar=$gPlayBackSlider')
            audio_name = cmds.timeControl(playback_slider, q=True, s=True)
            display_sounds = cmds.timeControl(
                playback_slider, q=True, displaySound=True
            )

            audio_nodes = []

            if audio_name:
                audio_nodes.append(pm.PyNode(audio_name))

            if not audio_name and display_sounds:
                start_frame = int(pm.playbackOptions(q=True, min=True))
                end_frame = float(pm.playbackOptions(q=True, max=True))
                frame_range = range(int(start_frame), int(end_frame))

                for node in pm.ls(type="audio"):
                    # Check if frame range and audio range intersections,
                    # for whether to include this audio node or not.
                    start_audio = node.offset.get()
                    end_audio = node.offset.get() + node.duration.get()
                    audio_range = range(int(start_audio), int(end_audio))

                    if bool(set(frame_range).intersection(audio_range)):
                        audio_nodes.append(node)

            instance.data["audio"] = []
            for node in audio_nodes:
                instance.data["audio"].append(
                    {
                        "offset": node.offset.get(),
                        "filename": node.filename.get()
                    }
                )
