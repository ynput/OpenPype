import pyblish.api
import pype.api


class ValidateTextureBatch(pyblish.api.ContextPlugin):
    """Validates that collected instnaces for Texture batch are OK.

        Validates:
            some textures are present
            workfile has resource files (optional)
            texture version matches to workfile version
            if texture name was parsed correctly
    """

    label = "Validate Texture Batch"
    hosts = ["standalonepublisher"]
    order = pype.api.ValidateContentsOrder
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
                file_name = instance.data["representations"][0]["files"][0]
                self._check_proper_collected(instance.data["versionData"],
                                             file_name)

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

    def _check_proper_collected(self, versionData, file_name):
        """
            Loop through collected versionData to check if name parsing was OK.
        Args:
            versionData: (dict)

        Returns:
            raises AssertionException
        """
        missing_key_values = []
        for key, value in versionData.items():
            if not value:
                missing_key_values.append(key)

        msg = "Collected data {} doesn't contain values for {}".format(
            versionData, missing_key_values) + "\n" + \
            "Name of the texture file doesn't match expected pattern.\n" + \
            "Please rename file(s) {}".format(file_name)

        assert not missing_key_values, msg
