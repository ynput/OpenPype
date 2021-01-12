import os
import nuke

# default write mov
nuke.knobDefault('Write.mov.colorspace', 'sRGB')


def filter_envvars_in_filepath(filename):
    """Expand variables in path such as ``$PROJECT_ROOT``.
    """
    expanded_path = os.path.expandvars(filename)
    return expanded_path


# register callback
nuke.addFilenameFilter(filter_envvars_in_filepath)
