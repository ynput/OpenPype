import hiero
import re
from pypeapp import config


def create_tag(key, value):
    """
    Creating Tag object.

    Args:
        key (str): name of tag
        value (dict): parameters of tag

    Returns:
        object: Tag object
    """

    tag = hiero.core.Tag(str(key))
    tag.setNote(value['note'])
    tag.setIcon(value['icon']['path'])
    mtd = tag.metadata()
    pres_mtd = value.get('metadata', None)
    if pres_mtd:
        [mtd.setValue("tag.{}".format(k), v)
         for k, v in pres_mtd.items()]

    return tag


def add_tags_from_presets():
    """
    Will create default tags from presets.
    """

    # get all presets
    presets = config.get_presets()

    # get nukestudio tag.json from presets
    nks_pres = presets['nukestudio']
    nks_pres_tags = nks_pres.get("tags", None)

    # get project and root bin object
    project = hiero.core.projects()[-1]
    root_bin = project.tagsBin()

    for _k, _val in nks_pres_tags.items():

        pattern = re.compile(r"\[(.*)\]")
        bin_find = pattern.findall(_k)
        if bin_find:
            # create Bin object
            bin = hiero.core.Bin(str(bin_find[0]))

            for k, v in _val.items():
                # create Tag obj
                tag = create_tag(k, v)

            # adding Tag to Bin
            bin.addItem(tag)

            # adding Tag to Root Bin
            root_bin.addItem(bin)

        else:
            print(_k, _val)
            # create Tag
            tag = create_tag(_k, _val)

            # adding Tag to Root Bin
            root_bin.addItem(tag)


add_tags_from_presets()
