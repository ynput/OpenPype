from pyblish import api
from pype.hosts import hiero as phiero

# from pype.hosts.hiero import lib
from pprint import pformat
# reload(phiero)
# reload(lib)


class CollectInstances(api.ContextPlugin):
    """Collect all Track items selection."""

    order = api.CollectorOrder - 0.5
    label = "Collect Instances"
    hosts = ["hiero"]

    def process(self, context):

        # only return enabled track items
        track_items = phiero.get_track_items(check_enabled=True)

        self.log.info(
            "Processing enabled track items: {}".format(len(track_items)))

        for _ti in track_items:
            data = dict()

            # get pype tag data
            tag_parsed_data = phiero.get_track_item_pype_data(_ti)
            self.log.debug(pformat(tag_parsed_data))

            if tag_parsed_data.get("id") != "pyblish.avalon.instance":
                continue
            # add tag data to instance data
            data.update({
                k: v for k, v in tag_parsed_data.items()
                if k not in ("id", "applieswhole", "label")
            })

            asset = tag_parsed_data["asset"]
            subset = tag_parsed_data["subset"]

            # insert family into families
            family = tag_parsed_data["family"]
            families = tag_parsed_data["families"]
            families.insert(0, family)

            track = _ti.parent()
            source = _ti.source().mediaSource()
            source_path = source.firstpath()
            file_head = source.filenameHead()
            file_info = next((f for f in source.fileinfos()), None)
            source_first_frame = int(file_info.startFrame())

            data.update({
                "name": "{}_{}".format(asset, subset),
                "asset": asset,
                "item": _ti,
                "families": families,

                # tags
                "tags": _ti.tags(),

                # track item attributes
                "track": track.name(),

                # source attribute
                "source": source,
                "sourcePath": source_path,
                "sourceFileHead": file_head,
                "sourceFirst": source_first_frame,
            })
            instance = context.create_instance(**data)
            self.log.info("Creating instance: {}".format(instance))
