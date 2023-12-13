import os

import pyblish.api
from pymxs import runtime as rt

from openpype.hosts.max.api import maintained_selection
from openpype.hosts.max.api.lib import get_operators
from openpype.pipeline import publish


class ExtractTyCache(publish.Extractor):
    """Extract tycache format with tyFlow operators.
    Notes:
        - TyCache only works for TyFlow Pro Plugin.

    Methods:
        self.get_export_particles_job_args(): sets up all job arguments
            for attributes to be exported in MAXscript

        self.get_operators(): get the export_particle operator

        self.get_files(): get the files with tyFlow naming convention
            before publishing
    """

    order = pyblish.api.ExtractorOrder - 0.2
    label = "Extract TyCache"
    hosts = ["max"]
    families = ["tycache", "tyspline"]

    def process(self, instance):
        # TODO: let user decide the param
        self.log.debug("Extracting Tycache...")

        stagingdir = self.staging_dir(instance)

        export_mode = instance.data.get("exportMode", 2)
        members = instance.data["members"]
        representations = instance.data.setdefault("representations", [])
        with maintained_selection():
            for operators in get_operators(members):
                operator, start_frame, end_frame, name = operators
                filename = f"{instance.name}_{name}.tyc"
                path = os.path.join(stagingdir, filename)
                filenames = self.get_files(
                    instance, name, start_frame, end_frame)
                job_args = self.get_export_particles_job_args(
                    operator, path, export_mode)
                for job in job_args:
                    rt.Execute(job)
                representation = {
                    'name': 'tyc',
                    'ext': 'tyc',
                    'files': filenames if len(filenames) > 1 else filenames[0],
                    "stagingDir": stagingdir
                }
                representations.append(representation)

                # Get the tyMesh filename for extraction
                mesh_filename = f"{instance.name}_{name}__tyMesh.tyc"
                mesh_repres = {
                    'name': 'tyMesh',
                    'ext': 'tyc',
                    'files': mesh_filename,
                    "stagingDir": stagingdir,
                    "outputName": 'tyMesh'
                }
                representations.append(mesh_repres)
                self.log.debug(
                    f"Extracted instance '{instance.name}' to: {filenames}")

    def get_files(self, instance, operator, start_frame, end_frame):
        """Get file names for tyFlow in tyCache format.

        Set the filenames accordingly to the tyCache file
        naming extension(.tyc) for the publishing purpose

        Actual File Output from tyFlow in tyCache format:
        <InstanceName>__tyPart_<frame>.tyc

        e.g. tycacheMain__tyPart_00000.tyc

        Args:
            instance (pyblish.api.Instance): instance.

        Returns:
            filenames(list): list of filenames

        """
        filenames = []
        for frame in range(int(start_frame), int(end_frame) + 1):
            filename = f"{instance.name}_{operator}__tyPart_{frame:05}.tyc"
            filenames.append(filename)
        return filenames

    def get_export_particles_job_args(self, operator, filepath,
                                      export_mode):
        """Sets up all job arguments for attributes.

        Those attributes are to be exported in MAX Script.

        Args:
            members (list): Member nodes of the instance.
            start (int): Start frame.
            end (int): End frame.
            filepath (str): Output path of the TyCache file.
            export_mode (int): Export Mode for the TyCache Output.

        Returns:
            list of arguments for MAX Script.

        """
        settings = {
            "exportMode": export_mode,
            "tycacheCreateObject": True,
            "tycacheCreateObjectIfNotCreated": True,
            "tyCacheFilename": filepath.replace("\\", "/")
        }

        job_args = []
        for key, value in settings.items():
            if isinstance(value, str):
                # embed in quotes
                value = f'"{value}"'

            job_args.append(f"{operator}.{key}={value}")
        job_args.append(f"{operator}.exportTyCache()")
        return job_args
