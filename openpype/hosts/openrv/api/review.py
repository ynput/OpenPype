"""review code"""
import os

import rv
import pymu

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


def extract_annotated_frame(filepath=None, annotated_frame=None):
    """Export frame to file
    """
    # TODO: Fix this QUADCYPRIEN
    marked_frames = rv.commands.markedFrames()
    annotated_frames = rv.extra_commands.findAnnotatedFrames()

    # Use set differences to figure out what frames we need to mark and unmark
    to_add = list(set(annotated_frames) - set(marked_frames))
    to_sub = list(set(marked_frames) - set(annotated_frames))

    # Generalize this into a function so you can reverse it after export.
    for frame_sub in to_sub:
        rv.commands.markFrame(frame_sub, False)
    for frame_add in to_add:
        if frame_add == annotated_frame:
            rv.commands.markFrame(frame_add, True)
    rv.commands.redraw()

    # Do your path substitution here
    os.fork()
    rv.runtime.eval("""
    require runtime;
    use rvtypes;
    {{
    runtime.load_module("export_utils");
    let Fname = runtime.intern_name("export_utils.exportMarkedFrames");
    (ExternalProcess;string,string) F = runtime.lookup_function(Fname);
     F("{0}", "default");
    }}
    """.format(filepath), [])
    os.wait()



def review_attributes(node=None):
    # TODO: Implement
    # prop_status = node + ".openpype" + ".review_status"
    # prop_comment = node + ".openpype" + ".review_comment"
    pass


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
