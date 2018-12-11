from maya import cmds
import pymel.core as pm

import pyblish.api
import avalon.api

class CollectReviewData(pyblish.api.InstancePlugin):
    """Collect Review data

    """

    order = pyblish.api.CollectorOrder + 0.3
    label = 'Collect Review Data'
    families = ["review"]

    def process(self, instance):

        # make ftrack publishable
        instance.data["families"] = ['ftrack']
        context = instance.context

        task = avalon.api.Session["AVALON_TASK"]
        # pseudo code

        # get cameras
        members = instance.data['setMembers']
        cameras = cmds.ls(members, long=True,
                          dag=True, cameras=True)
        self.log.debug('members: {}'.format(members))

        # validate required settings
        assert len(cameras) == 1, "Not a single camera found in extraction"
        camera = cameras[0]
        self.log.debug('camera: {}'.format(camera))

        objectset = context.data['objectsets']

        reviewable_subset = None
        reviewable_subset = list(set(members) & set(objectset))
        if reviewable_subset:
            assert len(reviewable_subset) <= 1, "Multiple subsets for review"
            self.log.debug('subset for review: {}'.format(reviewable_subset))

            for inst in context:
                self.log.debug('instance: {}'.format(instance))
                if inst.name == reviewable_subset[0]:
                    inst.data['families'].append('review')
                    inst.data['review_camera'] = camera
                    self.log.info('adding review family to {}'.format(reviewable_subset))
                    cmds.setAttr(str(instance) + '.active', 0)
                    inst.data['publish'] = 0
        else:
            instance.data['subset'] = task + 'Review'
            instance.data['review_camera'] = camera
