# -*- coding: utf-8 -*-
"""Abstract ExpectedFile class definition."""
from abc import ABCMeta, abstractmethod
import six


@six.add_metaclass(ABCMeta)
class ExpectedFiles:
    """Class grouping functionality for all supported renderers.

    Attributes:
        multipart (bool): Flag if multipart exrs are used.

    """

    multipart = False

    @abstractmethod
    def get(self, render_instance):
        """Get expected files for given renderer and render layer.

        This method should return dictionary of all files we are expecting
        to be rendered from the host. Usually `render_instance` corresponds
        to *render layer*. Result can be either flat list with the file
        paths or it can be list of dictionaries. Each key corresponds to
        for example AOV name or channel, etc.

        Example::

            ['/path/to/file.001.exr', '/path/to/file.002.exr']

            or as dictionary:

            [
                {
                    "beauty": ['/path/to/beauty.001.exr', ...],
                    "mask": ['/path/to/mask.001.exr']
                }
            ]


        Args:
            render_instance (:class:`RenderInstance`): Data passed from
                collector to determine files. This should be instance of
                :class:`abstract_collect_render.RenderInstance`

        Returns:
            list: Full paths to expected rendered files.
            list of dict: Path to expected rendered files categorized by
                AOVs, etc.

        """
        raise NotImplementedError()
