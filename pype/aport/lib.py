import pype.api as pype


def get_anatomy(**kwarg):
    return pype.Anatomy


def format_anatomy(data):
    from .templates import (
        get_anatomy
    )
    file = script_name()

    anatomy = get_anatomy()

    # TODO: perhaps should be in try!
    padding = anatomy.render.padding

    data.update({
        "hierarchy": pype.get_hierarchy(),
        "frame": "#" * padding,
        "VERSION": pype.get_version_from_workfile(file)
    })

    # log.info("format_anatomy:anatomy: {}".format(anatomy))
    return anatomy.format(data)
