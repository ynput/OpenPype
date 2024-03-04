import os
import pyblish.api
from pymxs import runtime as rt
from openpype.pipeline.publish import (
    RepairAction,
    ValidateContentsOrder,
    PublishValidationError,
    OptionalPyblishPluginMixin
)
from openpype.hosts.max.api.lib_rendersettings import RenderSettings


class ValidateRenderPasses(OptionalPyblishPluginMixin,
                           pyblish.api.InstancePlugin):
    """Validates Render Passes before Deadline Submission
    """

    order = ValidateContentsOrder
    families = ["maxrender"]
    hosts = ["max"]
    label = "Validate Render Passes"
    optional = True
    actions = [RepairAction]

    def process(self, instance):
        if not self.is_active(instance.data):
            return
        invalid = self.get_invalid(instance)
        if invalid:
            bullet_point_invalid_statement = "\n".join(
                f"- {err_type}: {filepath}" for err_type, filepath
                in invalid
            )
            report = (
                "Invalid render passes found.\n\n"
                f"{bullet_point_invalid_statement}\n\n"
                "You can use repair action to fix the invalid filepath."
            )
            raise PublishValidationError(
                report, title="Invalid Render Passes")

    @classmethod
    def get_invalid(cls, instance):
        """Function to get invalid beauty render outputs and
        render elements.

        1. Check Render Output Folder matches the name of
           the current Max Scene, e.g.
             The name of the current Max scene:
               John_Doe.max
             The expected render output directory:
               {root[work]}/{project[name]}/{hierarchy}/{asset}/
               work/{task[name]}/render/3dsmax/John_Doe/

        2. Check image extension(s) of the render output(s)
           matches the image format in OP/AYON setting, e.g.
               The current image format in settings: png
               The expected render outputs: John_Doe.png

        3. Check filename of render element ends with the name of
           render element from the 3dsMax Render Element Manager.
           e.g. The name of render element: RsCryptomatte
            The expected filename: {InstanceName}_RsCryptomatte.png

        Args:
            instance (pyblish.api.Instance): instance
            filename (str): filename of the Max scene

        Returns:
            list: list of invalid filename which doesn't match
                with the project name
        """
        invalid = []
        file = rt.maxFileName
        filename, ext = os.path.splitext(file)
        if filename not in rt.rendOutputFilename:
            cls.log.error(
                "Render output folder must include "
                f" the max scene name {filename} "
            )
            invalid_folder_name = os.path.dirname(
                rt.rendOutputFilename).replace(
                    "\\", "/").split("/")[-1]
            invalid.append(("Invalid Render Output Folder",
                            invalid_folder_name))
        beauty_fname = os.path.basename(rt.rendOutputFilename)
        beauty_name, ext = os.path.splitext(beauty_fname)
        invalid_filenames = cls.get_invalid_filenames(
            instance, beauty_name)
        invalid.extend(invalid_filenames)
        invalid_image_format = cls.get_invalid_image_format(
            instance, ext.lstrip("."))
        invalid.extend(invalid_image_format)
        renderer = instance.data["renderer"]
        if renderer in [
            "ART_Renderer",
            "Redshift_Renderer",
            "V_Ray_6_Hotfix_3",
            "V_Ray_GPU_6_Hotfix_3",
            "Default_Scanline_Renderer",
            "Quicksilver_Hardware_Renderer",
        ]:
            render_elem = rt.maxOps.GetCurRenderElementMgr()
            render_elem_num = render_elem.NumRenderElements()
            for i in range(render_elem_num):
                renderlayer_name = render_elem.GetRenderElement(i)
                renderpass = str(renderlayer_name).split(":")[-1]
                rend_file = render_elem.GetRenderElementFilename(i)
                if not rend_file:
                    cls.log.error(
                        f"No filepath for render element {renderpass}")
                    invalid.append((f"Invalid {renderpass}",
                                    "No filepath"))
                rend_fname, ext = os.path.splitext(
                    os.path.basename(rend_file))
                invalid_filenames = cls.get_invalid_filenames(
                    instance, rend_fname, renderpass=renderpass)
                invalid.extend(invalid_filenames)
                invalid_image_format = cls.get_invalid_image_format(
                    instance, ext)
                invalid.extend(invalid_image_format)
        elif renderer == "Arnold":
            cls.log.debug(
                "Renderpass validation does not support Arnold yet,"
                " validation skipped...")

        return invalid

    @classmethod
    def get_invalid_filenames(cls, instance, file_name, renderpass=None):
        """Function to get invalid filenames from render outputs.

        Args:
            instance (pyblish.api.Instance): instance
            file_name (str): name of the file
            renderpass (str, optional): name of the renderpass.
                Defaults to None.

        Returns:
            list: invalid filenames
        """
        invalid = []
        if instance.name not in file_name:
            cls.log.error("The renderpass should have instance name inside.")
            invalid.append((f"Invalid instance name",
                            file_name))
        if renderpass is not None:
            if not file_name.rstrip(".").endswith(renderpass):
                cls.log.error(
                    f"Filename for {renderpass} should "
                    f"end with {renderpass}"
                )
                invalid.append((f"Invalid {renderpass}",
                                os.path.basename(file_name)))
        return invalid

    @classmethod
    def get_invalid_image_format(cls, instance, ext):
        """Function to check if the image format of the render outputs
        aligns with that in the setting.

        Args:
            instance (pyblish.api.Instance): instance
            ext (str): image extension

        Returns:
            list: list of files with invalid image format
        """
        invalid = []
        settings = instance.context.data["project_settings"].get("max")
        image_format = settings["RenderSettings"]["image_format"]
        ext = ext.lstrip(".")
        if ext != image_format:
            msg = (
                f"Invalid image format {ext} for render outputs.\n"
                f"Should be: {image_format}")
            cls.log.error(msg)
            invalid.append((msg, ext))
        return invalid

    @classmethod
    def repair(cls, instance):
        container = instance.data.get("instance_node")
        # TODO: need to rename the function of render_output
        RenderSettings().render_output(container)
        cls.log.debug("Finished repairing the render output "
                      "folder and filenames.")
