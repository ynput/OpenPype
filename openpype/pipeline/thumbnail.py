import os
import copy
import logging

from openpype import AYON_SERVER_ENABLED
from openpype.lib import Logger
from openpype.client import get_project
from . import legacy_io
from .anatomy import Anatomy
from .plugin_discover import (
    discover,
    register_plugin,
    register_plugin_path,
)


def get_thumbnail_binary(thumbnail_entity, thumbnail_type, dbcon=None):
    if not thumbnail_entity:
        return

    log = Logger.get_logger(__name__)
    resolvers = discover_thumbnail_resolvers()
    resolvers = sorted(resolvers, key=lambda cls: cls.priority)
    if dbcon is None:
        dbcon = legacy_io

    for Resolver in resolvers:
        available_types = Resolver.thumbnail_types
        if (
            thumbnail_type not in available_types
            and "*" not in available_types
            and (
                isinstance(available_types, (list, tuple))
                and len(available_types) == 0
            )
        ):
            continue
        try:
            instance = Resolver(dbcon)
            result = instance.process(thumbnail_entity, thumbnail_type)
            if result:
                return result

        except Exception:
            log.warning("Resolver {0} failed durring process.".format(
                Resolver.__class__.__name__, exc_info=True
            ))


class ThumbnailResolver(object):
    """Determine how to get data from thumbnail entity.

    "priority" - determines the order of processing in `get_thumbnail_binary`,
        lower number is processed earlier.
    "thumbnail_types" - it is expected that thumbnails will be used in more
        more than one level, there is only ["thumbnail"] type at the moment
        of creating this docstring but it is expected to add "ico" and "full"
        in future.
    """

    priority = 100
    thumbnail_types = ["*"]

    def __init__(self, dbcon):
        self._log = None
        self.dbcon = dbcon

    @property
    def log(self):
        if self._log is None:
            self._log = logging.getLogger(self.__class__.__name__)
        return self._log

    def process(self, thumbnail_entity, thumbnail_type):
        pass


class TemplateResolver(ThumbnailResolver):
    priority = 90

    def process(self, thumbnail_entity, thumbnail_type):
        template = thumbnail_entity["data"].get("template")
        if not template:
            self.log.debug("Thumbnail entity does not have set template")
            return

        thumbnail_root_format_key = "{thumbnail_root}"
        thumbnail_root = os.environ.get("AVALON_THUMBNAIL_ROOT") or ""
        # Check if template require thumbnail root and if is avaiable
        if thumbnail_root_format_key in template and not thumbnail_root:
            return

        project_name = self.dbcon.active_project()
        project = get_project(project_name, fields=["name", "data.code"])

        template_data = copy.deepcopy(
            thumbnail_entity["data"].get("template_data") or {}
        )
        template_data.update({
            "_id": str(thumbnail_entity["_id"]),
            "thumbnail_type": thumbnail_type,
            "thumbnail_root": thumbnail_root,
            "project": {
                "name": project["name"],
                "code": project["data"].get("code")
            },
        })
        # Add anatomy roots if is in template
        if "{root" in template:
            anatomy = Anatomy(project_name)
            template_data["root"] = anatomy.roots

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
    def process(self, thumbnail_entity, thumbnail_type):
        return thumbnail_entity["data"].get("binary_data")


class ServerThumbnailResolver(ThumbnailResolver):
    _cache = None

    @classmethod
    def _get_cache(cls):
        if cls._cache is None:
            from openpype.client.server.thumbnails import AYONThumbnailCache

            cls._cache = AYONThumbnailCache()
        return cls._cache

    def process(self, thumbnail_entity, thumbnail_type):
        if not AYON_SERVER_ENABLED:
            return None
        data = thumbnail_entity["data"]
        entity_type = data.get("entity_type")
        entity_id = data.get("entity_id")
        if not entity_type or not entity_id:
            return None

        import ayon_api

        project_name = self.dbcon.active_project()
        thumbnail_id = thumbnail_entity["_id"]

        cache = self._get_cache()
        filepath = cache.get_thumbnail_filepath(project_name, thumbnail_id)
        if filepath:
            with open(filepath, "rb") as stream:
                return stream.read()

        # This is new way how thumbnails can be received from server
        #   - output is 'ThumbnailContent' object
        # NOTE Use 'get_server_api_connection' because public function
        #   'get_thumbnail_by_id' does not return output of 'ServerAPI'
        #   method.
        con = ayon_api.get_server_api_connection()
        if hasattr(con, "get_thumbnail_by_id"):
            result = con.get_thumbnail_by_id(thumbnail_id)
            if result.is_valid:
                filepath = cache.store_thumbnail(
                    project_name,
                    thumbnail_id,
                    result.content,
                    result.content_type
                )
        else:
            # Backwards compatibility for ayon api where 'get_thumbnail_by_id'
            #   is not implemented and output is filepath
            filepath = con.get_thumbnail(
                project_name, entity_type, entity_id, thumbnail_id
            )

        if not filepath:
            return None

        with open(filepath, "rb") as stream:
            return stream.read()


# Thumbnail resolvers
def discover_thumbnail_resolvers():
    return discover(ThumbnailResolver)


def register_thumbnail_resolver(plugin):
    register_plugin(ThumbnailResolver, plugin)


def register_thumbnail_resolver_path(path):
    register_plugin_path(ThumbnailResolver, path)


register_thumbnail_resolver(TemplateResolver)
register_thumbnail_resolver(BinaryThumbnail)
register_thumbnail_resolver(ServerThumbnailResolver)
