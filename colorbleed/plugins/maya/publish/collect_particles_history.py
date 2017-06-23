import maya.cmds as cmds

import pyblish.api


class CollectParticlesHistory(pyblish.api.InstancePlugin):
    """For a Particle system collect the history.

    This would collect its nucleus and cache files.

    """

    order = pyblish.api.CollectorOrder + 0.499
    families = ['colorbleed.particles']
    label = "Particles History"

    def process(self, instance):

        # Include history of the instancer
        particles = cmds.ls(instance, dag=True, shapes=True,
                            leaf=True, long=True)
        particles = cmds.ls(particles, type="nParticle", long=True)
        if not particles:
            self.log.info("No particles found")
            return

        export = particles

        # Get the required inputs of the particles from its history
        particles_history = cmds.listHistory(particles) or []
        if particles_history:
            nucleus = cmds.ls(particles_history, type="nucleus")
            export.extend(nucleus)
            caches = cmds.ls(particles_history, type="cacheFile")
            export.extend(caches)

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
