from maya import cmds

import pyblish.api


class CollectAssData(pyblish.api.InstancePlugin):
    """Collect Ass data."""

    order = pyblish.api.CollectorOrder + 0.2
    label = 'Collect Ass'
    families = ["ass"]

    def process(self, instance):
        objsets = instance.data['setMembers']

        for objset in objsets:
            objset = str(objset)
            members = cmds.sets(objset, query=True)
            if members is None:
                self.log.warning("Skipped empty instance: \"%s\" " % objset)
                continue
            if "content_SET" in objset:
                instance.data['setMembers'] = members
                self.log.debug('content members: {}'.format(members))
            elif objset.startswith("proxy_SET"):
                assert len(members) == 1, "You have multiple proxy meshes, please only use one"
                instance.data['proxy'] = members
                self.log.debug('proxy members: {}'.format(members))

        self.log.debug("data: {}".format(instance.data))
