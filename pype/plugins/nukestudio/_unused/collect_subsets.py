from pyblish import api


class CollectClipSubsets(api.InstancePlugin):
    """Collect Subsets from selected Clips, Tags, Preset."""

    order = api.CollectorOrder + 0.01
    label = "Collect Subsets"
    hosts = ["nukestudio"]
    families = ['clip']

    def process(self, instance):
        tags = instance.data.get('tags', None)
        presets = instance.context.data['presets'][
            instance.context.data['host']]
        if tags:
            self.log.info(tags)

        if presets:
            self.log.info(presets)

        # get presets and tags
        # iterate tags and get task family
        # iterate tags and get host family
        # iterate tags and get handles family

        instance = instance.context.create_instance(instance_name)

        instance.data.update({
            "subset": subset_name,
            "stagingDir": staging_dir,
            "task": task,
            "representation": ext[1:],
            "host": host,
            "asset": asset_name,
            "label": label,
            "name": name,
            # "hierarchy": hierarchy,
            # "parents": parents,
            "family": family,
            "families": [families, 'ftrack'],
            "publish": True,
            # "files": files_list
        })
        instances.append(instance)
