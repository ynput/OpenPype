import json
import logging
import os

from maya import cmds  # noqa

from openpype.hosts.maya.api.lib import evaluation

log = logging.getLogger(__name__)

# The maya alembic export types
ALEMBIC_ARGS = {
    "attr": (list, tuple),
    "attrPrefix": (list, tuple),
    "autoSubd": bool,
    "dataFormat": str,
    "dontSkipUnwrittenFrames": bool,
    "endFrame": float,
    "eulerFilter": bool,
    "frameRange": str,  # "start end"; overrides startFrame & endFrame
    "frameRelativeSample": float,
    "melPerFrameCallback": str,
    "melPostJobCallback": str,
    "noNormals": bool,
    "preRoll": bool,
    "preRollStartFrame": int,
    "pythonPerFrameCallback": str,
    "pythonPostJobCallback": str,
    "renderableOnly": bool,
    "root": (list, tuple),
    "selection": bool,
    "startFrame": float,
    "step": float,
    "stripNamespaces": bool,
    "userAttr": (list, tuple),
    "userAttrPrefix": (list, tuple),
    "uvWrite": bool,
    "uvsOnly": bool,
    "verbose": bool,
    "wholeFrameGeo": bool,
    "worldSpace": bool,
    "writeColorSets": bool,
    "writeCreases": bool,  # Maya 2015 Ext1+
    "writeFaceSets": bool,
    "writeUVSets": bool,   # Maya 2017+
    "writeVisibility": bool,
}


def extract_alembic(
    file,
    attr=None,
    attrPrefix=None,
    dataFormat="ogawa",
    endFrame=None,
    eulerFilter=True,
    frameRange="",
    noNormals=False,
    preRoll=False,
    preRollStartFrame=0,
    renderableOnly=False,
    root=None,
    selection=True,
    startFrame=None,
    step=1.0,
    stripNamespaces=True,
    uvWrite=True,
    verbose=False,
    wholeFrameGeo=False,
    worldSpace=False,
    writeColorSets=False,
    writeCreases=False,
    writeNormals=False,
    writeFaceSets=False,
    writeUVSets=False,
    writeVisibility=False
):
    """Extract a single Alembic Cache.

    This extracts an Alembic cache using the `-selection` flag to minimize
    the extracted content to solely what was Collected into the instance.

    Arguments:

        startFrame (float): Start frame of output. Ignored if `frameRange`
            provided.

        endFrame (float): End frame of output. Ignored if `frameRange`
            provided.

        frameRange (tuple or str): Two-tuple with start and end frame or a
            string formatted as: "startFrame endFrame". This argument
            overrides `startFrame` and `endFrame` arguments.

        eulerFilter (bool): When on, X, Y, and Z rotation data is filtered with
            an Euler filter. Euler filtering helps resolve irregularities in
            rotations especially if X, Y, and Z rotations exceed 360 degrees.
            Defaults to True.

        noNormals (bool): When on, normal data from the original polygon
            objects is not included in the exported Alembic cache file.

        preRoll (bool): This frame range will not be sampled.
            Defaults to False.

        renderableOnly (bool): When on, any non-renderable nodes or hierarchy,
            such as hidden objects, are not included in the Alembic file.
            Defaults to False.

        selection (bool): Write out all all selected nodes from the
            active selection list that are descendents of the roots specified
            with -root. Defaults to False.

        uvWrite (bool): When on, UV data from polygon meshes and subdivision
            objects are written to the Alembic file. Only the current UV map is
            included.

        writeColorSets (bool): Write all color sets on MFnMeshes as
            color 3 or color 4 indexed geometry parameters with face varying
            scope. Defaults to False.

        writeFaceSets (bool): Write all Face sets on MFnMeshes.
            Defaults to False.

        wholeFrameGeo (bool): Data for geometry will only be written
            out on whole frames. Defaults to False.

        worldSpace (bool): When on, the top node in the node hierarchy is
            stored as world space. By default, these nodes are stored as local
            space. Defaults to False.

        writeVisibility (bool): Visibility state will be stored in
            the Alembic file.  Otherwise everything written out is treated as
            visible. Defaults to False.

        writeUVSets (bool): Write all uv sets on MFnMeshes as vector
            2 indexed geometry parameters with face varying scope. Defaults to
            False.

        writeCreases (bool): If the mesh has crease edges or crease
            vertices, the mesh (OPolyMesh) would now be written out as an OSubD
            and crease info will be stored in the Alembic file. Otherwise,
            creases info won't be preserved in Alembic file unless a custom
            Boolean attribute SubDivisionMesh has been added to mesh node and
            its value is true. Defaults to False.

        dataFormat (str): The data format to use for the cache,
                          defaults to "ogawa"

        step (float): The time interval (expressed in frames) at
            which the frame range is sampled. Additional samples around each
            frame can be specified with -frs. Defaults to 1.0.

        attr (list of str, optional): A specific geometric attribute to write
            out. Defaults to [].

        attrPrefix (list of str, optional): Prefix filter for determining which
            geometric attributes to write out. Defaults to ["ABC_"].

        root (list of str): Maya dag path which will be parented to
            the root of the Alembic file. Defaults to [], which means the
            entire scene will be written out.

        stripNamespaces (bool): When on, any namespaces associated with the
            exported objects are removed from the Alembic file. For example, an
            object with the namespace taco:foo:bar appears as bar in the
            Alembic file.

        verbose (bool): When on, outputs frame number information to the
            Script Editor or output window during extraction.

        preRollStartFrame (float): The frame to start scene
            evaluation at.  This is used to set the starting frame for time
            dependent translations and can be used to evaluate run-up that
            isn't actually translated. Defaults to 0.
    """

    # Ensure alembic exporter is loaded
    cmds.loadPlugin('AbcExport', quiet=True)

    # Alembic Exporter requires forward slashes
    file = file.replace('\\', '/')

    # Ensure list arguments are valid.
    attr = attr or []
    attrPrefix = attrPrefix or []
    root = root or []

    # Pass the start and end frame on as `frameRange` so that it
    # never conflicts with that argument
    if not frameRange:
        # Fallback to maya timeline if no start or end frame provided.
        if startFrame is None:
            startFrame = cmds.playbackOptions(query=True,
                                              animationStartTime=True)
        if endFrame is None:
            endFrame = cmds.playbackOptions(query=True,
                                            animationEndTime=True)

        # Ensure valid types are converted to frame range
        assert isinstance(startFrame, ALEMBIC_ARGS["startFrame"])
        assert isinstance(endFrame, ALEMBIC_ARGS["endFrame"])
        frameRange = "{0} {1}".format(startFrame, endFrame)
    else:
        # Allow conversion from tuple for `frameRange`
        if isinstance(frameRange, (list, tuple)):
            assert len(frameRange) == 2
            frameRange = "{0} {1}".format(frameRange[0], frameRange[1])

    # Assemble options
    options = {
        "selection": selection,
        "frameRange": frameRange,
        "eulerFilter": eulerFilter,
        "noNormals": noNormals,
        "preRoll": preRoll,
        "renderableOnly": renderableOnly,
        "uvWrite": uvWrite,
        "writeColorSets": writeColorSets,
        "writeFaceSets": writeFaceSets,
        "wholeFrameGeo": wholeFrameGeo,
        "worldSpace": worldSpace,
        "writeVisibility": writeVisibility,
        "writeUVSets": writeUVSets,
        "writeCreases": writeCreases,
        "dataFormat": dataFormat,
        "step": step,
        "attr": attr,
        "attrPrefix": attrPrefix,
        "stripNamespaces": stripNamespaces,
        "verbose": verbose,
        "preRollStartFrame": preRollStartFrame
    }

    # Validate options
    for key, value in options.copy().items():

        # Discard unknown options
        if key not in ALEMBIC_ARGS:
            log.warning("extract_alembic() does not support option '%s'. "
                        "Flag will be ignored..", key)
            options.pop(key)
            continue

        # Validate value type
        valid_types = ALEMBIC_ARGS[key]
        if not isinstance(value, valid_types):
            raise TypeError("Alembic option unsupported type: "
                            "{0} (expected {1})".format(value, valid_types))

        # Ignore empty values, like an empty string, since they mess up how
        # job arguments are built
        if isinstance(value, (list, tuple)):
            value = [x for x in value if x.strip()]

            # Ignore option completely if no values remaining
            if not value:
                options.pop(key)
                continue

            options[key] = value

    # The `writeCreases` argument was changed to `autoSubd` in Maya 2018+
    maya_version = int(cmds.about(version=True))
    if maya_version >= 2018:
        options['autoSubd'] = options.pop('writeCreases', False)

    # Format the job string from options
    job_args = list()
    for key, value in options.items():
        if isinstance(value, (list, tuple)):
            for entry in value:
                job_args.append("-{} {}".format(key, entry))
        elif isinstance(value, bool):
            # Add only when state is set to True
            if value:
                job_args.append("-{0}".format(key))
        else:
            job_args.append("-{0} {1}".format(key, value))

    job_str = " ".join(job_args)
    job_str += ' -file "%s"' % file

    # Ensure output directory exists
    parent_dir = os.path.dirname(file)
    if not os.path.exists(parent_dir):
        os.makedirs(parent_dir)

    if verbose:
        log.debug("Preparing Alembic export with options: %s",
                  json.dumps(options, indent=4))
        log.debug("Extracting Alembic with job arguments: %s", job_str)

    # Perform extraction
    print("Alembic Job Arguments : {}".format(job_str))

    # Disable the parallel evaluation temporarily to ensure no buggy
    # exports are made. (PLN-31)
    # TODO: Make sure this actually fixes the issues
    with evaluation("off"):
        cmds.AbcExport(j=job_str, verbose=verbose)

    if verbose:
        log.debug("Extracted Alembic to: %s", file)

    return file
