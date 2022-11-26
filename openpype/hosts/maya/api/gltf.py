# -*- coding: utf-8 -*-
"""Tools to work with GLTF."""
import logging

from maya import cmds, mel  # noqa

log = logging.getLogger(__name__)

_gltf_options = {
    "of" : str,                  # outputFolder
    "cpr" : str,                 # copyright
    "sno" : bool,                # selectedNodeOnly
    "sn" : str,                  # sceneName
    "glb" : bool,                # binary
    "nbu" : bool,                # niceBufferURIs
    "hbu" : bool,                # hashBufferURI
    "ext" : bool,                # externalTextures
    "ivt" : int,                 # initialValuesTime
    "acn" : str,                 # animationClipName
    "ast" : int,                 # animationClipStartTime
    "aet" : int,                 # animationClipEndTime
    "afr" : float,               # animationClipFrameRate
    "dsa" : int,                 # detectStepAnimations
    "mpa" : str,                 # meshPrimitiveAttributes
    "bpa" : str,                 # blendPrimitiveAttributes
    "i32" : bool,                # force32bitIndices
    "ssm" : bool,                # skipStandardMaterials
    "eut": bool,                 # excludeUnusedTexcoord
    "dm" : bool,                 # defaultMaterial
    "cm" : bool,                 # colorizeMaterials
    "dmy" : str,                 # dumpMaya
    "dgl" : str,                 # dumpGLTF
    "imd" : str,                 # ignoreMeshDeformers
    "ssc" : bool,                # skipSkinClusters
    "sbs" : bool,                # skipBlendShapes
    "rvp" : bool,                # redrawViewport
    "vno" : bool                 # visibleNodesOnly
}


def extract_gltf(parent_dir,
                 filename,
                 **kwargs):

    """Sets GLTF export options from data in the instance.

    """

    cmds.loadPlugin('maya2glTF', quiet=True)
    # load the UI to run mel command
    mel.eval("maya2glTF_UI()")

    parent_dir = parent_dir.replace('\\', '/')
    options = {
        "dsa": 1,
        "glb": True
    }
    options.update(kwargs)

    for key, value in options.copy().items():
        if key not in _gltf_options:
            log.warning("extract_gltf() does not support option '%s'. "
                        "Flag will be ignored..", key)
            options.pop(key)
            options.pop(value)
            continue

    job_args = list()
    default_opt = "maya2glTF -of \"{0}\" -sn \"{1}\"".format(parent_dir, filename) # noqa
    job_args.append(default_opt)

    for key, value in options.items():
        if isinstance(value, str):
            job_args.append("-{0} \"{1}\"".format(key, value))
        elif isinstance(value, bool):
            if value:
                job_args.append("-{0}".format(key))
        else:
            job_args.append("-{0} {1}".format(key, value))

    job_str = " ".join(job_args)
    log.info("{}".format(job_str))
    mel.eval(job_str)

    # close the gltf export after finish the export
    gltf_UI = "maya2glTF_exporter_window"
    if cmds.window(gltf_UI, q=True, exists=True):
        cmds.deleteUI(gltf_UI)
