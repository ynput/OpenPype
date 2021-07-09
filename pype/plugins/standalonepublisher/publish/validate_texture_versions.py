import pyblish.api
import pype.api


class ValidateTextureBatchVersions(pyblish.api.ContextPlugin):
    """Validates that versions match in workfile and textures."""
    label = "Validate Texture Batch Versions"
    hosts = ["standalonepublisher"]
    order = pype.api.ValidateContentsOrder
    families = ["workfile", "textures"]
    optional = True

    def process(self, context):

        workfiles = []
        workfiles_in_textures = []
        processed_versions = set()
        for instance in context:
            if instance.data["family"] == "workfile":
                workfiles.append(instance.data["representations"][0]["files"])

                processed_versions.add(instance.data["version"])

            if instance.data["family"] == "textures":
                wfile = instance.data["versionData"]["workfile"]
                workfiles_in_textures.append(wfile)

                version_str = "v{:03d}".format(instance.data["version"])
                if 'DUMMY' in wfile:
                    self.log.warning("Textures are missing attached workfile")
                else:
                    assert version_str in wfile, \
                        "Not matching version, texture {} - workfile {}".format(
                            instance.data["version"], wfile
                        )
                processed_versions.add(instance.data["version"])

        msg = "Not matching set of workfiles and textures." + \
              "{} not equal to {}".format(set(workfiles),
                                          set(workfiles_in_textures)) +\
              "\nCheck that both workfile and textures are present"

        keys = set(workfiles) == set(workfiles_in_textures)
        assert keys, msg

        ver_msg = "Too many versions publishing. "\
                  "Publish only single version at time!"
        assert len(processed_versions) == 1, ver_msg

        self.log.info("Processed versions {} matching.".
                      format(processed_versions))
