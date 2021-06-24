import pyblish.api
import openpype.api


class ValidateTextureBatch(pyblish.api.ContextPlugin):
    """Validates that collected instnaces for Texture batch are OK.

        Validates:
            some textures are present
            workfile has resource files (optional)
            texture version matches to workfile version
    """

    label = "Validate Texture Batch"
    hosts = ["standalonepublisher"]
    order = openpype.api.ValidateContentsOrder
    families = ["workfile", "textures"]

    def process(self, context):

        workfiles = []
        workfiles_in_textures = []
        for instance in context:
            if instance.data["family"] == "workfile":
                workfiles.append(instance.data["representations"][0]["files"])

                if not instance.data.get("resources"):
                    msg = "No resources for workfile {}".\
                           format(instance.data["name"])
                    self.log.warning(msg)

            if instance.data["family"] == "textures":
                wfile = instance.data["versionData"]["workfile"]
                workfiles_in_textures.append(wfile)

                version_str = "v{:03d}".format(instance.data["version"])
                assert version_str in wfile, \
                    "Not matching version, texture {} - workfile {}".format(
                        instance.data["version"], wfile
                    )

        msg = "Not matching set of workfiles and textures." + \
              "{} not equal to {}".format(set(workfiles),
                                          set(workfiles_in_textures)) +\
              "\nCheck that both workfile and textures are present"
        keys = set(workfiles) == set(workfiles_in_textures)
        assert keys, msg
