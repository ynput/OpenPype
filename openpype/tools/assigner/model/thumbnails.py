import os

from openpype.client import get_thumbnails
from openpype.pipeline.thumbnail import get_thumbnail_binary

from .common import AssignerToolSubModel


class ThumbnailsModel(AssignerToolSubModel):
    def __init__(self, *args, **kwargs):
        super(ThumbnailsModel, self).__init__(*args, **kwargs)

        self._default_thumbnail_content = None

        self._cached_thumbnails_by_id = {}

    @property
    def default_thumbnail_content(self):
        if self._default_thumbnail_content is None:
            filepath = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                "images",
                "default_thumbnail.png"
            )
            with open(filepath, "rb") as stream:
                content = stream.read()
            self._default_thumbnail_content = content
        return self._default_thumbnail_content

    def get_thumbnail_sources(self, thumbnail_ids):
        if not thumbnail_ids:
            return [self.default_thumbnail_content]

        thumbnail_ids_s = set(thumbnail_ids)
        if None in thumbnail_ids_s:
            thumbnail_ids_s.remove(None)
        if not thumbnail_ids_s:
            return [self.default_thumbnail_content]

        output = []
        thumbnail_docs = get_thumbnails(self.project_name, thumbnail_ids)
        for thumbnail_doc in thumbnail_docs:
            image = get_thumbnail_binary(
                thumbnail_doc, "thumbnail", self.dbcon
            )
            if image:
                output.append(image)

        if not output:
            output.append(self.default_thumbnail_content)
        return output

    def get_thumbnail_source(self, thumbnail_id):
        return self.get_thumbnail_sources([thumbnail_id])[0]
