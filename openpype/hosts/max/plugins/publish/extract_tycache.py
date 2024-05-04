import os

import pyblish.api
from pymxs import runtime as rt

from openpype.hosts.max.api import maintained_selection
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
    families = ["tycache"]

    def process(self, instance):
        # TODO: let user decide the param
        start = int(instance.context.data["frameStart"])
        end = int(instance.context.data.get("frameEnd"))
        self.log.debug("Extracting Tycache...")

        stagingdir = self.staging_dir(instance)
        filename = "{name}.tyc".format(**instance.data)
        path = os.path.join(stagingdir, filename)
        filenames = self.get_files(instance, start, end)
        additional_attributes = instance.data.get("tyc_attrs", {})

        with maintained_selection():
            job_args = self.get_export_particles_job_args(
                instance.data["members"],
                start, end, path,
                additional_attributes)
            for job in job_args:
                rt.Execute(job)
        representations = instance.data.setdefault("representations", [])
        representation = {
            'name': 'tyc',
            'ext': 'tyc',
            'files': filenames if len(filenames) > 1 else filenames[0],
            "stagingDir": stagingdir,
        }
        representations.append(representation)

        # Get the tyMesh filename for extraction
        mesh_filename = f"{instance.name}__tyMesh.tyc"
        mesh_repres = {
            'name': 'tyMesh',
            'ext': 'tyc',
            'files': mesh_filename,
            "stagingDir": stagingdir,
            "outputName": '__tyMesh'
        }
        representations.append(mesh_repres)

        # Get the material filename of which assigned in
        # tyCache for extraction
        material_filename = f"{instance.name}__tyMtl.mat"
        full_material_name = os.path.join(stagingdir, material_filename)
        full_material_name = full_material_name.replace("\\", "/")
        if os.path.exists(full_material_name):
            mateiral_repres = {
                "name": 'tyMtl',
                "ext": 'mat',
                'files': material_filename,
                'stagingDir': stagingdir,
                "outputName": '__tyMtl'
            }
            representations.append(mateiral_repres)

        self.log.debug(f"Extracted instance '{instance.name}' to: {filenames}")

    def get_files(self, instance, start_frame, end_frame):
        """Get file names for tyFlow in tyCache format.

        Set the filenames accordingly to the tyCache file
        naming extension(.tyc) for the publishing purpose

        Actual File Output from tyFlow in tyCache format:
        <InstanceName>__tyPart_<frame>.tyc

        e.g. tycacheMain__tyPart_00000.tyc

        Args:
            instance (pyblish.api.Instance): instance.
            start_frame (int): Start frame.
            end_frame (int): End frame.

        Returns:
            filenames(list): list of filenames

        """
        filenames = []
        for frame in range(int(start_frame), int(end_frame) + 1):
            filename = f"{instance.name}__tyPart_{frame:05}.tyc"
            filenames.append(filename)
        return filenames

    def get_export_particles_job_args(self, members, start, end,
                                      filepath, additional_attributes):
        """Sets up all job arguments for attributes.

        Those attributes are to be exported in MAX Script.

        Args:
            members (list): Member nodes of the instance.
            start (int): Start frame.
            end (int): End frame.
            filepath (str): Output path of the TyCache file.
            additional_attributes (dict): channel attributes data
                which needed to be exported

        Returns:
            list of arguments for MAX Script.

        """
        settings = {
            "exportMode": 2,
            "frameStart": start,
            "frameEnd": end,
            "tyCacheFilename": filepath.replace("\\", "/")
        }
        settings.update(additional_attributes)

        job_args = []
        for operator in self.get_operators(members):
            for key, value in settings.items():
                if isinstance(value, str):
                    # embed in quotes
                    value = f'"{value}"'

                job_args.append(f"{operator}.{key}={value}")
            job_args.append(f"{operator}.exportTyCache()")
        return job_args

    @staticmethod
    def get_operators(members):
        """Get Export Particles Operator.

        Args:
            members (list): Instance members.

        Returns:
            list of particle operators

        """
        opt_list = []
        for member in members:
            obj = member.baseobject
            # TODO: see if it can use maxscript instead
            anim_names = rt.GetSubAnimNames(obj)
            for anim_name in anim_names:
                sub_anim = rt.GetSubAnim(obj, anim_name)
                boolean = rt.IsProperty(sub_anim, "Export_Particles")
                if boolean:
                    event_name = sub_anim.Name
                    opt = f"${member.Name}.{event_name}.export_particles"
                    opt_list.append(opt)

        return opt_list
