import os

import pyblish.api
from pymxs import runtime as rt

from openpype.hosts.max.api import maintained_selection
from openpype.pipeline import publish


class ExtractTyCache(publish.Extractor):
    """
    Extract tycache format with tyFlow operators.
    Notes:
        - TyCache only works for TyFlow Pro Plugin.

    Args:
        self.export_particle(): sets up all job arguments for attributes
            to be exported in MAXscript

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
        start = int(instance.context.data.get("frameStart"))
        end = int(instance.context.data.get("frameEnd"))
        self.log.info("Extracting Tycache...")

        stagingdir = self.staging_dir(instance)
        filename = "{name}.tyc".format(**instance.data)
        path = os.path.join(stagingdir, filename)
        filenames = self.get_file(path, start, end)
        with maintained_selection():
            job_args = None
            if instance.data["tycache_type"] == "tycache":
                job_args = self.export_particle(
                    instance.data["members"],
                    start, end, path)
            elif instance.data["tycache_type"] == "tycachespline":
                job_args = self.export_particle(
                    instance.data["members"],
                    start, end, path,
                    tycache_spline_enabled=True)

            for job in job_args:
                rt.Execute(job)

        representation = {
            'name': 'tyc',
            'ext': 'tyc',
            'files': filenames if len(filenames) > 1 else filenames[0],
            "stagingDir": stagingdir
        }
        instance.data["representations"].append(representation)
        self.log.info(f"Extracted instance '{instance.name}' to: {filenames}")

    def get_file(self, filepath, start_frame, end_frame):
        filenames = []
        filename = os.path.basename(filepath)
        orig_name, _ = os.path.splitext(filename)
        for frame in range(int(start_frame), int(end_frame) + 1):
            actual_name = "{}_{:05}".format(orig_name, frame)
            actual_filename = filepath.replace(orig_name, actual_name)
            filenames.append(os.path.basename(actual_filename))

        return filenames

    def export_particle(self, members, start, end,
                        filepath, tycache_spline_enabled=False):
        """Sets up all job arguments for attributes.

        Those attributes are to be exported in MAX Script.

        Args:
            members (list): Member nodes of the instance.
            start (int): Start frame.
            end (int): End frame.
            filepath (str): Output path of the TyCache file.

        Returns:
            list of arguments for MAX Script.

        """
        job_args = []
        opt_list = self.get_operators(members)
        for operator in opt_list:
            if tycache_spline_enabled:
                export_mode = f'{operator}.exportMode=3'
                has_tyc_spline = f'{operator}.tycacheSplines=true'
                job_args.extend([export_mode, has_tyc_spline])
            else:
                export_mode = f'{operator}.exportMode=2'
                job_args.append(export_mode)
            start_frame = f"{operator}.frameStart={start}"
            job_args.append(start_frame)
            end_frame = f"{operator}.frameEnd={end}"
            job_args.append(end_frame)
            filepath = filepath.replace("\\", "/")
            tycache_filename = f'{operator}.tyCacheFilename="{filepath}"'
            job_args.append(tycache_filename)
            # TODO: add the additional job args for tycache attributes
            tycache_export = f"{operator}.exportTyCache()"
            job_args.append(tycache_export)

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
        # TODO: to see if it can be used maxscript instead
            anim_names = rt.GetSubAnimNames(obj)
            for anim_name in anim_names:
                sub_anim = rt.GetSubAnim(obj, anim_name)
                boolean = rt.IsProperty(sub_anim, "Export_Particles")
                if boolean:
                    event_name = sub_anim.Name
                    opt = f"${member.Name}.{event_name}.export_particles"
                    opt_list.append(opt)

        return opt_list
