import json

from avalon import api
import unreal


class AnimationCollectionLoader(api.Loader):
    """Load Unreal SkeletalMesh from FBX"""

    families = ["setdress"]
    representations = ["json"]

    label = "Load Animation Collection"
    icon = "cube"
    color = "orange"

    def load(self, context, name, namespace, options):
        from avalon import api, pipeline
        from avalon.unreal import lib
        from avalon.unreal import pipeline as unreal_pipeline
        import unreal

        # Create directory for asset and avalon container
        root = "/Game/Avalon/Assets"
        asset = context.get('asset').get('name')
        suffix = "_CON"

        tools = unreal.AssetToolsHelpers().get_asset_tools()
        asset_dir, container_name = tools.create_unique_asset_name(
            "{}/{}".format(root, asset), suffix="")

        container_name += suffix

        unreal.EditorAssetLibrary.make_directory(asset_dir)

        libpath = self.fname

        with open(libpath, "r") as fp:
            data = json.load(fp)

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

            api.load(
                loader,
                reference,
                namespace=instance_name,
                options=element
            )

        # Create Asset Container
        lib.create_avalon_container(
            container=container_name, path=asset_dir)

        data = {
            "schema": "openpype:container-2.0",
            "id": pipeline.AVALON_CONTAINER_ID,
            "asset": asset,
            "namespace": asset_dir,
            "container_name": container_name,
            "loader": str(self.__class__.__name__),
            "representation": context["representation"]["_id"],
            "parent": context["representation"]["parent"],
            "family": context["representation"]["context"]["family"]
        }
        unreal_pipeline.imprint(
            "{}/{}".format(asset_dir, container_name), data)

        asset_content = unreal.EditorAssetLibrary.list_assets(
            asset_dir, recursive=True, include_folder=True
        )

        return asset_content

    def update(self, container, representation):
        from avalon import api, io
        from avalon.unreal import pipeline

        source_path = api.get_representation_path(representation)

        with open(source_path, "r") as fp:
            data = json.load(fp)

        animation_containers = [
            i for i in pipeline.ls() if
            i.get('asset') == container.get('asset') and
            i.get('family') == 'animation']

        for element in data:
            new_version = io.find_one({"_id": io.ObjectId(element.get('_id'))})
            new_version_number = new_version.get('context').get('version')
            anim_container = None
            for i in animation_containers:
                if i.get('container_name') == (element.get('subset') + "_CON"):
                    anim_container = i
                    break
            if not anim_container:
                continue

            api.update(anim_container, new_version_number)

        container_path = "{}/{}".format(container["namespace"],
                                        container["objectName"])
        # update metadata
        pipeline.imprint(
            container_path,
            {
                "representation": str(representation["_id"]),
                "parent": str(representation["parent"])
            })

    def remove(self, container):
        unreal.EditorAssetLibrary.delete_directory(container["namespace"])
