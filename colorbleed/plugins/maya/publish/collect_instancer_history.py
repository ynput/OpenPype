import pyblish.api
import maya.cmds as cmds


class CollectInstancerHistory(pyblish.api.InstancePlugin):
    """For an Instancer collect the history.

    This would collect its particles with nucleus and cacheFile

    """

    order = pyblish.api.CollectorOrder + 0.49
    families = ['colorbleed.instancer']
    label = "Instancer History"

    def process(self, instance):

        members = instance.data["setMembers"]

        # Include history of the instancer
        instancers = cmds.ls(members, type="instancer")
        if not instancers:
            self.log.info("No instancers found")
            return

        export = instancers[:]

        # Get the required inputs of the particles from history
        history = cmds.listHistory(instancers) or []
        particles = cmds.ls(history, type="nParticle")
        export.extend(particles)
        if particles:
            self.log.info("Particles: {0}".format(particles))

            particles_history = cmds.listHistory(particles) or []
            self.log.debug("Particle history: {0}".format(particles_history))

            nucleus = cmds.ls(particles_history, long=True, type="nucleus")
            self.log.info("Collected nucleus: {0}".format(nucleus))
            export.extend(nucleus)

            caches = cmds.ls(particles_history, long=True, type="cacheFile")
            self.log.info("Collected caches: {0}".format(caches))
            export.extend(caches)

        # Collect input shapes for the instancer
        for instancer in cmds.ls(instancers, exactType="instancer", long=True):
            attr = "{}.inputHierarchy".format(instancer)
            inputs = cmds.listConnections(attr, source=True,
                                          destination=False) or []
            export.extend(inputs)

        # Add it to the instance
        data = instance[:]
        data.extend(export)
        # Ensure unique objects only
        data = list(set(data))
        self.log.info("Setting members to {0}".format(data))
        instance[:] = data

        # Store the recommended export selection so the export can do it
        # accordingly
        instance.data["exactExportMembers"] = export
