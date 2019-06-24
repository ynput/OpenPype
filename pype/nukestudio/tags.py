import re

from pypeapp import (
    config,
    Logger
)
from avalon import io

import hiero

log = Logger().get_logger(__name__, "nukestudio")

_hierarchy_orig = 'hierarchy_orig'


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

    return update_tag(tag, value)


def update_tag(tag, value):
    """
    Fixing Tag object.

    Args:
        tag (obj): Tag object
        value (dict): parameters of tag
    """

    tag.setNote(value['note'])
    tag.setIcon(str(value['icon']['path']))
    mtd = tag.metadata()
    pres_mtd = value.get('metadata', None)
    if pres_mtd:
        [mtd.setValue("tag.{}".format(str(k)), str(v))
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

    # Get project task types.
    tasks = io.find_one({"type": "project"})["config"]["tasks"]
    nks_pres_tags["[Tasks]"] = {}
    for task in tasks:
        nks_pres_tags["[Tasks]"][task["name"]] = {
            "editable": "1",
            "note": "Tag note",
            "icon": {
                "path": ""
            },
            "metadata": {
                "family": "task"
            }
        }

    # get project and root bin object
    project = hiero.core.projects()[-1]
    root_bin = project.tagsBin()

    for _k, _val in nks_pres_tags.items():
        pattern = re.compile(r"\[(.*)\]")
        bin_find = pattern.findall(_k)
        if bin_find:
            # check what is in root bin
            bins = [b for b in root_bin.items()
                    if b.name() in str(bin_find[0])]

            if bins:
                bin = bins[0]
            else:
                # create Bin object
                bin = hiero.core.Bin(str(bin_find[0]))

            for k, v in _val.items():
                tags = [t for t in bin.items()
                        if str(k) in t.name()
                        if len(str(k)) == len(t.name())]
                if not tags:
                    # create Tag obj
                    tag = create_tag(k, v)

                    # adding Tag to Bin
                    bin.addItem(tag)
                else:
                    update_tag(tags[0], v)

            if not bins:
                # adding Tag to Root Bin
                root_bin.addItem(bin)

        else:
            tags = None
            tags = [t for t in root_bin.items()
                    if str(_k) in t.name()]

            if not tags:
                # create Tag
                tag = create_tag(_k, _val)

                # adding Tag to Root Bin
                root_bin.addItem(tag)
            else:
                # check if Hierarchy in name
                # update Tag if already exists
                tag_names = [tg.name().lower() for tg in tags]
                for _t in tags:
                    if 'hierarchy' not in _t.name().lower():
                        # update only non hierarchy tags
                        # because hierarchy could be edited
                        update_tag(_t, _val)
                    elif _hierarchy_orig in _t.name().lower():
                        # if hierarchy_orig already exists just
                        # sync with preset
                        update_tag(_t, _val)
                    else:
                        # if history tag already exist then create
                        # backup synchronisable original Tag
                        if (_hierarchy_orig not in tag_names):
                            # create Tag obj
                            tag = create_tag(
                                _hierarchy_orig.capitalize(), _val
                            )

                            # adding Tag to Bin
                            root_bin.addItem(tag)
