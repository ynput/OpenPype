import os
import copy
import logging

from openpype.client import get_project
from . import legacy_io
from .plugin_discover import (
    discover,
    register_plugin,
    register_plugin_path,
)
log = logging.getLogger(__name__)


def get_thumbnail_binary(thumbnail_entity, thumbnail_type, dbcon=None):
    if not thumbnail_entity:
        return

    resolvers = discover_thumbnail_resolvers()
    resolvers = sorted(resolvers, key=lambda cls: cls.order)
    if dbcon is None:
        dbcon = legacy_io

    for Resolver in resolvers:
        try:
            instance = Resolver(dbcon)
            result = instance.process(thumbnail_entity, thumbnail_type)
            if result:
                return result

        except Exception:
            log.warning("Resolver {0} failed durring process.".format(
                Resolver.__class__.__name__, exc_info=True
            ))


class ThumbnailsCache(object):
    def cache_thumbnail(self, thumbnail_id, content):
        return

    def get_thumbnail(self, thumbnail_id):
        return None


class ThumbnailsContext(object):
    def __init__(self, project_name=None):
        self._cache = None
        self._resolvers = None

        self._project_name = project_name

        self._create_cache()

    def _create_cache(self):
        self._cache = ThumbnailsCache()

    def cache_thumbnail(self, thumbnail_id, content):
        if self._cache is None:
            return
        return self._cache.cache_thumbnail(thumbnail_id, content)

    def get_cached_thumbnail(self, thumbnail_id):
        if self._cache is None:
            return None
        return self._cache.get_thumbnail(thumbnail_id)

    def get_thumbnail_binaries(self, thumbnail_docs_by_id):
        remainder_docs = {
            str(doc_id): copy.deepcopy(doc)
            for doc_id, doc in thumbnail_docs_by_id.items()
        }
        output = {}
        for thumbnail_id in tuple(remainder_docs.keys()):
            content = self.get_cached_thumbnail(thumbnail_id)
            if content is not None:
                remainder_docs.pop(thumbnail_id)
                output[thumbnail_id] = content

        if not remainder_docs:
            return output

        for resolver in self.get_resolvers():
            if not remainder_docs:
                break
            tmp_output = resolver.get_thumbnail_binaries(remainder_docs)
            for doc_id, content in tmp_output.items():
                if content is not None:
                    remainder_docs.pop(doc_id)
                    output[doc_id] = content
                    self.cache_thumbnail(thumbnail_id, content)

        return output

    def get_resolvers(self):
        if self._resolvers is None:
            resolver_classes = discover_thumbnail_resolvers()
            resolvers = []
            for resolver_class in resolver_classes:
                try:
                    resolvers.append(resolver_class(self))
                except Exception:
                    self.log.warning(
                        "Failed to initialize thumbnail resolver {}".format(
                            resolver_class.__name__
                        )
                    )
            self._resolvers = list(sorted(
                resolvers,
                key=lambda resolver: resolver.order
            ))
        return self._resolvers

    def refresh(self):
        self._resolvers = None

    def set_project(self, project_name):
        if self._project_name == project_name:
            return

        self._project_name = project_name
        for resolver in self._resolvers:
            resolver.refresh()


class ThumbnailResolver(object):
    """Determine how to get data from thumbnail entity.

    Properties:
        order (int) Determines the order of processing. Lower number
            is processed earlier.

    Args:
        context (ThumbnailsContext): Context which created resolver.
    """

    order = 100
    _log = None

    def __init__(self, context):
        self._context = context

    @property
    def context(self):
        """Quick access to thumbnails context."""

        return self._context

    @property
    def project_name(self):
        """Project name in which thumbnails are located."""

        return self.context.project_name

    def refresh(self):
        """Possible refresh of resolver for example on project change."""
        return

    @property
    def log(self):
        """Quick access to logger on object."""

        if self._log is None:
            self._log = logging.getLogger(self.__class__.__name__)
        return self._log

    def get_thumbnail_binaries(self, thumbnail_docs_by_id):
        self.log.warning(
            "Using deprecated method 'process' in thumbnail resolver."
        )
        return {
            doc_id: self.process(thumbnail_entity, None)
            for doc_id, thumbnail_entity in thumbnail_docs_by_id.items()
        }

    def process(self, thumbnail_entity, thumbnail_type):
        """Resolve binary thumbnail based on thumbnail document and type.

        Warning:
            This is for backwards compatibility. Please override
                'get_thumbnail_binaries'.

        Args:
            thumbnail_entity (Dict[str, Any]): Thumbnail document which
                describes how thumbnails
        """

        pass


class TemplateResolver(ThumbnailResolver):
    order = 90

    def __init__(self, *args, **kwargs):
        super(TemplateResolver, self).__init__(*args, **kwargs)

        self._root = None
        self._project_doc = None

    def refresh(self):
        self._project_doc = None

    def _refresh(self):
        self._root = os.environ.get("AVALON_THUMBNAIL_ROOT")
        self._project_doc = get_project(
            self.project_name, fields=["name", "data.code"]
        )

    def get_thumbnail_binaries(self, thumbnail_docs_by_id):
        return {
            doc_id: self.get_thumbnail_binary(thumbnail_doc)
            for doc_id, thumbnail_doc in thumbnail_docs_by_id.items()
        }

    def process(self, thumbnail_entity, thumbnail_type):
        return self.get_thumbnail_binary(thumbnail_entity)

    def get_thumbnail_binary(self, thumbnail_doc):
        if self._project_doc is None:
            self._refresh()

        if not self._root:
            return

        template = thumbnail_doc["data"].get("template")
        if not template:
            self.log.debug("Thumbnail entity does not have set template")
            return

        template_data = copy.deepcopy(
            thumbnail_doc["data"].get("template_data") or {}
        )
        template_data.update({
            "_id": str(thumbnail_doc["_id"]),
            "thumbnail_type": "thumbnail",
            "thumbnail_root": self._root,
            "project": {
                "name": self._project_doc["name"],
                "code": self._project_doc["data"].get("code")
            }
        })

        try:
            filepath = os.path.normpath(template.format(**template_data))
        except KeyError:
            self.log.warning((
                "Missing template data keys for template <{0}> || Data: {1}"
            ).format(template, str(template_data)))
            return

        if not os.path.exists(filepath):
            self.log.warning("File does not exist \"{0}\"".format(filepath))
            return

        with open(filepath, "rb") as _file:
            content = _file.read()

        return content


class BinaryThumbnail(ThumbnailResolver):
    def get_thumbnail_binaries(self, thumbnail_docs_by_id):
        return {
            doc_id: thumbnail_doc["data"].get("binary_data")
            for doc_id, thumbnail_doc in thumbnail_docs_by_id.items()
        }


# Thumbnail resolvers
def discover_thumbnail_resolvers():
    return discover(ThumbnailResolver)


def register_thumbnail_resolver(plugin):
    register_plugin(ThumbnailResolver, plugin)


def register_thumbnail_resolver_path(path):
    register_plugin_path(ThumbnailResolver, path)


register_thumbnail_resolver(TemplateResolver)
register_thumbnail_resolver(BinaryThumbnail)
