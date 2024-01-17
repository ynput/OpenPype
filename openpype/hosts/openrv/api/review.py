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


def extract_annotated_frame(filepath=None, frame_to_export=None):
    """Export frame to file
    """
    current_frame = rv.commands.frameStart()
    sources = rv.commands.sourcesAtFrame(current_frame)
    current_source = rv.commands.sourceMediaInfo(sources[0])
    start_frame = current_source['startFrame']
    # Rv framerange representation = [120=1, 121=2, etc...]{frame=rvframe}
    # There is no 0 value at start
    frame_to_export = frame_to_export - start_frame + 1

    marked_frames = rv.commands.markedFrames()
    annotated_frames = rv.extra_commands.findAnnotatedFrames()

    # Generalize this into a function so you can reverse it after export.
    for marked_frame in marked_frames:
        rv.commands.markFrame(marked_frame, False)

    for annotated_frame in annotated_frames:
        if (annotated_frame - start_frame + 1) == frame_to_export:
            rv.commands.markFrame(annotated_frame, True)
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

    for marked_frame in marked_frames:
        rv.commands.markFrame(marked_frame, True)

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
