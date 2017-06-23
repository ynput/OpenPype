import os
import shutil

import pyblish_cb.lib
import colorbleed.api


class IntegrateColorbleedAssets(colorbleed.api.Integrator):
    """Name and position instances on disk for instances.

    The files are transferred from the `extractDir` to the
    computed `integrationDir` and are renamed as:
        - "{item}_{family}_{subsetName}_{version}.{ext}"

    Assumptions:
        - Each extracted instance is 1 file (no directories)

    """

    label = "Asset"
    families = ["colorbleed.model", "colorbleed.rig", "colorbleed.pointcache",
                "colorbleed.proxy", "colorbleed.layout", "colorbleed.look",
                "colorbleed.vrmeshReplace", "colorbleed.review",
                "colorbleed.instancer", "colorbleed.camera",
                "colorbleed.mayaAscii",
                "colorbleed.furYeti"]

    def process(self, instance):
        super(IntegrateColorbleedAssets, self).process(instance)

        self.log.info("Integrating {0}..".format(instance))

        integration = pyblish_cb.lib.compute_integration(instance)

        # Store reference for upcoming plug-ins
        instance.data["integrationDir"] = integration['path']
        instance.data["integrationVersion"] = integration['versionNum']

        path = integration['path']
        data = integration.copy()

        try:
            if not os.path.exists(path):
                os.makedirs(path)

            self.log.info("Moving files to %s" % path)

            tmp = instance.data["extractDir"]
            for src in (os.path.join(tmp, f) for f in os.listdir(tmp)):

                self.log.debug("Integrating %s" % src)

                # Source must be a file
                if not os.path.isfile(src):
                    self.log.error("Source is not a file: {0}".format(src))
                    continue

                # TODO(marcus): Consider files without extension
                data["ext"] = src.split(".", 1)[-1]
                dst = os.path.join(path, "{item}_"
                                         "{family}_"
                                         "{subsetName}_"
                                         "{version}.{ext}".format(
                                            **data))

                # Copy
                self.log.info("\"%s\" -> \"%s\"" % (src, dst))
                shutil.copyfile(src, dst)

            self.log.debug("Tagged %s with .Version" % path)

            try:
                subset_path = os.path.dirname(path)
                cquery.tag(subset_path, ".Subset")
                self.log.debug("Tagged %s with .Subset" % subset_path)
            except cquery.TagExists:
                pass

        except OSError as e:
            # If, for whatever reason, this instance did not get written.
            instance.data.pop("integrationDir")
            raise e

        except Exception as e:
            raise Exception("An unknown error occured: %s" % e)
