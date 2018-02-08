import os

import pyblish.api


class ValidateFileNames(pyblish.api.Validator):
    """Ensure all file names follow the same structure

    Filename should have identifiable parts:
        - name ( example: Avengers_shot010_preview )
        - frame ( example: #### )
        - extension ( example: tiff )

    The result when rendering frame 1250 would be as follows:
        Avengers_shot010_preview.1250.tiff

    When certain parts need to be rendered out separately for some reason it
    is advisable to something all the lines of:
        Avengers_shot010_character_beauty.1250.tiff
    """

    order = pyblish.api.ValidatorOrder
    label = "Validate File Names (Saver)"
    families = ["colorbleed.imagesequence"]
    hosts = ["fusion"]

    @classmethod
    def get_invalid(cls, instance):

        invalid = []

        path = instance.data["path"]
        basename = os.path.basename(path)

        parts = basename.split(".")
        if len(parts) != 3:
            invalid.append(instance)
            cls.log.error("%s has %i parts, should be 3"
                          % (instance, len(parts)))
        else:
            is_numbers = all(i.isdigit() for i in parts[1])
            if len(parts[1]) != 4 or not is_numbers:
                cls.log.error("Number padding is not four digits")
                invalid.append(instance)

        return invalid

    def process(self, instance):
        invalid = self.get_invalid(instance)
        if invalid:
            raise RuntimeError("Found %i instances with a wrong file name "
                               "structure" % len(invalid))
