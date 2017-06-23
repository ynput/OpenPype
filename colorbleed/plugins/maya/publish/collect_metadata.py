import pyblish.api
import copy


class CollectMetadata(pyblish.api.ContextPlugin):
    """Transfer context metadata to the instance.
    
    This applies a copy of the `context.data['metadata']` to the
    `instance.data['metadata']` for the following metadata:
    
    Provides:
        {
            "topic": "topic",
            "author": "user",
            "date": "date",
            "filename": "currentFile"
        }


    """
    order = pyblish.api.CollectorOrder + 0.2
    label = "Metadata"

    mapping = {"topic": "topic",
               "author": "user",
               "date": "date",
               "filename": "currentFile"}

    def process(self, context):

        metadata = {}
        for key, source in self.mapping.iteritems():
            if source in context.data:
                metadata[key] = context.data.get(source)

        for instance in context:
            instance.data["metadata"] = copy.deepcopy(metadata)

        self.log.info("Collected {0}".format(metadata))
