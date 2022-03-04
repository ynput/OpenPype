# -*- coding: utf-8 -*-
import unreal  # noqa


class OpenPypeUnrealException(Exception):
    pass


@unreal.uclass()
class OpenPypeHelpers(unreal.OpenPypeLib):
    """Class wrapping some useful functions for OpenPype.

    This class is extending native BP class in OpenPype Integration Plugin.

    """

    @unreal.ufunction(params=[str, unreal.LinearColor, bool])
    def set_folder_color(self, path: str, color: unreal.LinearColor) -> None:
        """Set color on folder in Content Browser.

        This method sets color on folder in Content Browser. Unfortunately
        there is no way to refresh Content Browser so new color isn't applied
        immediately. They are saved to config file and appears correctly
        only after Editor is restarted.

        Args:
            path (str): Path to folder
            color (:class:`unreal.LinearColor`): Color of the folder

        Example:

            OpenPypeHelpers().set_folder_color(
                "/Game/Path", unreal.LinearColor(a=1.0, r=1.0, g=0.5, b=0)
            )

        Note:
            This will take effect only after Editor is restarted. I couldn't
            find a way to refresh it. Also this saves the color definition
            into the project config, binding this path with color. So if you
            delete this path and later re-create, it will set this color
            again.

        """
        self.c_set_folder_color(path, color, False)
