"""review code"""
import os

import rv


def get_path_annotated_frame(frame=None, asset=None, asset_folder=None):
    """Get path for annotations
    """
    # TODO: This should be less hardcoded
    filename = os.path.normpath(
        "{}/pyblish/exports/annotated_frames/annotate_{}_{}.jpg".format(
            str(asset_folder),
            str(asset),
            str(frame)
        )
    )
    return filename


def extract_annotated_frame(filepath=None):
    """Export frame to file
    """
    if filepath:
        return rv.commands.exportCurrentFrame(filepath)


def review_attributes(node=None):
    prop_status = node + ".openpype" + ".review_status"
    prop_comment = node + ".openpype" + ".review_comment"


def get_review_attribute(node=None, attribute=None):
    attr = node + ".openpype" + "." + attribute
    return rv.commands.getStringProperty(attr)[0]


def write_review_attribute(node=None, attribute=None, att_value=None):
    att_prop = node + ".openpype" + ".{}".format(attribute)
    if not rv.commands.propertyExists(att_prop):
        rv.commands.newProperty(att_prop, rv.commands.StringType, 1)
    rv.commands.setStringProperty(att_prop, [str(att_value)], True)


def export_current_view_frame(frame=None, export_path=None):
    rv.commands.setFrame(int(frame))
    rv.commands.exportCurrentFrame(export_path)
