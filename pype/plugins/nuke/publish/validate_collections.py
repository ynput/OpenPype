import pyblish.api
import pype.api
import clique

import os
import glob


class ValidateCollections(pyblish.api.InstancePlugin):
    """Validates mapped resources.

    These are external files to the current application, for example
    these could be textures, image planes, cache files or other linked
    media.

    This validates:
        - The resources are existing files.
        - The resources have correctly collected the data.

    """

    order = pype.api.ValidateContentsOrder
    label = "Validate Collections"
    families = ['prerendered.frames']

    def process(self, instance):

        collections, remainder = clique.assemble(*instance.data['files'])
        self.log.info('collections: {}'.format(collections))

        assert len(collections) == 1, "There are multiple collections in the folder"
        collection_instance = instance.data.get('collection', None)

        assert collections[0].is_contiguous(),"Some frames appear to be missing"
