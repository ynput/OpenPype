import os
import json
import contextlib

from maya import cmds

import pyblish_maya
import colorbleed.api


@contextlib.contextmanager
def suspension():
    try:
        cmds.refresh(suspend=True)
        yield
    finally:
        cmds.refresh(suspend=False)


class ExtractAlembic(colorbleed.api.Extractor):
    """Extract Alembic Cache

    This extracts an Alembic cache using the `-selection` flag to minimize
    the extracted content to solely what was Collected into the instance.

    Arguments:

        startFrame (float): Start frame of output. Ignored if `frameRange`
            provided.

        endFrame (float): End frame of output. Ignored if `frameRange`
            provided.

        frameRange (str): Frame range in the format of "startFrame endFrame".
            Overrides `startFrame` and `endFrame` arguments.

        dataFormat (str): The data format to use for the cache,
                          defaults to "ogawa"

        verbose (bool): When on, outputs frame number information to the
            Script Editor or output window during extraction.

        noNormals (bool): When on, normal data from the original polygon
            objects is not included in the exported Alembic cache file.

        renderableOnly (bool): When on, any non-renderable nodes or hierarchy,
            such as hidden objects, are not included in the Alembic file.
            Defaults to False.

        stripNamespaces (bool): When on, any namespaces associated with the
            exported objects are removed from the Alembic file. For example, an
            object with the namespace taco:foo:bar appears as bar in the
            Alembic file.

        uvWrite (bool): When on, UV data from polygon meshes and subdivision
            objects are written to the Alembic file. Only the current UV map is
            included.

        worldSpace (bool): When on, the top node in the node hierarchy is
            stored as world space. By default, these nodes are stored as local
            space. Defaults to False.

        eulerFilter (bool): When on, X, Y, and Z rotation data is filtered with
            an Euler filter. Euler filtering helps resolve irregularities in
            rotations especially if X, Y, and Z rotations exceed 360 degrees.
            Defaults to True.
    """

    label = "Alembic"
    families = ["colorbleed.model",
                "colorbleed.pointcache",
                "colorbleed.animation",
                "colorbleed.proxy"]
    optional = True

    @property
    def options(self):
        """Overridable options for Alembic export

        Given in the following format
            - {NAME: EXPECTED TYPE}

        If the overridden option's type does not match,
        the option is not included and a warning is logged.

        """

        return {"startFrame": float,
                "endFrame": float,
                "frameRange": str,
                # "start end"; overrides startFrame & endFrame
                "eulerFilter": bool,
                "frameRelativeSample": float,
                "noNormals": bool,
                "renderableOnly": bool,
                "step": float,
                "stripNamespaces": bool,
                "uvWrite": bool,
                "wholeFrameGeo": bool,
                "worldSpace": bool,
                "writeVisibility": bool,
                "writeColorSets": bool,
                "writeFaceSets": bool,
                "writeCreases": bool,  # Maya 2015 Ext1+
                "dataFormat": str,
                "root": (list, tuple),
                "attr": (list, tuple),
                "attrPrefix": (list, tuple),
                "userAttr": (list, tuple),
                "melPerFrameCallback": str,
                "melPostJobCallback": str,
                "pythonPerFrameCallback": str,
                "pythonPostJobCallback": str,
                "selection": bool}

    @property
    def default_options(self):
        """Supply default options to extraction.

        This may be overridden by a subclass to provide
        alternative defaults.

        """

        start_frame = cmds.playbackOptions(query=True, animationStartTime=True)
        end_frame = cmds.playbackOptions(query=True, animationEndTime=True)

        return {"startFrame": start_frame,
                "endFrame": end_frame,
                "selection": True,
                "uvWrite": True,
                "eulerFilter": True,
                "dataFormat": "ogawa"  # ogawa, hdf5
                }

    def process(self, instance):
        # Ensure alembic exporter is loaded
        cmds.loadPlugin('AbcExport', quiet=True)

        parent_dir = self.staging_dir(instance)
        filename = "%s.abc" % instance.name
        path = os.path.join(parent_dir, filename)

        # Alembic Exporter requires forward slashes
        path = path.replace('\\', '/')

        options = self.default_options
        options["userAttr"] = ("uuid",)
        options = self.parse_overrides(instance, options)

        job_str = self.parse_options(options)
        job_str += ' -file "%s"' % path

        self.log.info('Extracting alembic to:  "%s"' % path)

        verbose = instance.data('verbose', False)
        if verbose:
            self.log.debug('Alembic job string: "%s"' % job_str)

        if not os.path.exists(parent_dir):
            os.makedirs(parent_dir)
        # import pprint
        # print("START DEBUG")
        # print(">>> SET MEMBERS")
        # pprint.pprint(instance.data["setMembers"])
        # print("END DEBUG")

        with suspension():
            with pyblish_maya.maintained_selection():
                self.log.debug(
                    "Preparing %s for export using the following options: %s\n"
                    "and the following string: %s"
                    % (list(instance),
                       json.dumps(options, indent=4),
                       job_str))
                cmds.select(instance.data("setMembers"), hierarchy=True)
                cmds.AbcExport(j=job_str, verbose=verbose)

    def parse_overrides(self, instance, options):
        """Inspect data of instance to determine overridden options

        An instance may supply any of the overridable options
        as data, the option is then added to the extraction.

        """

        for key in instance.data():
            if key not in self.options:
                continue

            # Ensure the data is of correct type
            value = instance.data(key)
            if not isinstance(value, self.options[key]):
                self.log.warning(
                    "Overridden attribute {key} was of "
                    "the wrong type: {invalid_type} "
                    "- should have been {valid_type}".format(
                        key=key,
                        invalid_type=type(value).__name__,
                        valid_type=self.options[key].__name__))
                continue

            options[key] = value

        return options

    @classmethod
    def parse_options(cls, options):
        """Convert key-word arguments to job arguments string

        Args:
            options (dict): the options for the command
        """

        # Convert `startFrame` and `endFrame` arguments
        if 'startFrame' in options or 'endFrame' in options:
            start_frame = options.pop('startFrame', None)
            end_frame = options.pop('endFrame', None)

            if 'frameRange' in options:
                cls.log.debug("The `startFrame` and/or `endFrame` arguments "
                              "are overridden by the provided `frameRange`.")
            elif start_frame is None or end_frame is None:
                cls.log.warning("The `startFrame` and `endFrame` arguments "
                                "must be supplied together.")
            else:
                options['frameRange'] = "%s %s" % (start_frame, end_frame)

        job_args = list()
        for key, value in options.items():
            if isinstance(value, (list, tuple)):
                for entry in value:
                    job_args.append("-%s %s" % (key, entry))
            elif isinstance(value, bool):
                job_args.append("-%s" % key)
            else:
                job_args.append("-%s %s" % (key, value))

        job_str = " ".join(job_args)

        return job_str
