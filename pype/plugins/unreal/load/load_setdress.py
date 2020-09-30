import json

from avalon import unreal as avalon_unreal
from avalon import api, io
import unreal


class AnimationCollectionLoader(api.Loader):
    """Load Unreal SkeletalMesh from FBX"""

    families = ["setdress"]
    representations = ["json"]

    label = "Load Animation Collection"
    icon = "cube"
    color = "orange"

    def load(self, context, name, namespace, options):
        # Necessary because I think Python imports api from avalon_unreal
        # as well. This forces it to use the right api.
        from avalon import api
        libpath = self.fname

        with open(libpath, "r") as fp:
            data = json.load(fp)

        print(api)

        all_loaders = api.discover(api.Loader)

        for element in data:
            reference = element.get('_id')

            loaders = api.loaders_from_representation(all_loaders, reference)
            loader = None
            for l in loaders:
                if l.__name__ == "AnimationFBXLoader":
                    loader = l
                    break

            if not loader:
                continue

            instance_name = element.get('instance_name')

            element_container = api.load(
                loader,
                reference,
                namespace=instance_name,
                options=element
            )
