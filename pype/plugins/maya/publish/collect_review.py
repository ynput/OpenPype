from maya import cmds
import pymel.core as pm

import pyblish.api
import avalon.api


class CollectReview(pyblish.api.InstancePlugin):
    """Collect Review data

    """

    order = pyblish.api.CollectorOrder + 0.3
    label = 'Collect Review Data'
    families = ["review"]

    def process(self, instance):

        self.log.debug('instance: {}'.format(instance))

        task = avalon.api.Session["AVALON_TASK"]

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

                self.log.debug('processing {}'.format(inst))
                self.log.debug('processing2 {}'.format(instance.context[i]))
                data = instance.context[i].data

                if inst.name == reviewable_subset[0]:
                    if data.get('families'):
                        data['families'].append('review')
                    else:
                        data['families'] = ['review']
                    self.log.debug('adding review family to {}'.format(reviewable_subset))
                    data['review_camera'] = camera
                    # data["publish"] = False
                    data['startFrameReview'] = instance.data["frameStart"]
                    data['endFrameReview'] = instance.data["frameEnd"]
                    data["frameStart"] = instance.data["frameStart"]
                    data["frameEnd"] = instance.data["frameEnd"]
                    data['handles'] = instance.data['handles']
                    data['step'] = instance.data['step']
                    data['fps'] = instance.data['fps']
                    cmds.setAttr(str(instance) + '.active', 1)
                    self.log.debug('data {}'.format(instance.context[i].data))
                    instance.context[i].data.update(data)
                    instance.data['remove'] = True
                i += 1
        else:
            instance.data['subset'] = task + 'Review'
            instance.data['review_camera'] = camera
            instance.data['startFrameReview'] = instance.data["frameStart"]
            instance.data['endFrameReview'] = instance.data["frameEnd"]

            # make ftrack publishable
            instance.data["families"] = ['ftrack']

            cmds.setAttr(str(instance) + '.active', 1)
