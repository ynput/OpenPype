import collections
import contextlib

import arrow
import ayon_api

from openpype.style import get_default_entity_icon_color
from openpype.tools.ayon_utils.models import NestedCacheItem
from openpype.tools.ayon_loader.abstract import (
    VersionItem,
    ProductItem,
    ProductTypeItem,
)

PRODUCTS_MODEL_SENDER = "products.model"


def version_item_from_entity(version):
    version_attribs = version["attrib"]
    frame_start = version_attribs.get("frameStart")
    frame_end = version_attribs.get("frameEnd")
    handle_start = version_attribs.get("handleStart")
    handle_end = version_attribs.get("handleEnd")
    step = version_attribs.get("step")

    frame_range = None
    duration = None
    handles = None
    if frame_start is not None and frame_end is not None:
        # Remove superfluous zeros from numbers (3.0 -> 3) to improve
        # readability for most frame ranges
        frame_start = int(frame_start)
        frame_end = int(frame_end)
        frame_range = "{}-{}".format(frame_start, frame_end)
        duration = frame_end - frame_start + 1

    if handle_start is not None and handle_end is not None:
        handles = "{}-{}".format(int(handle_start), int(handle_end))

    # NOTE There is also 'updatedAt', should be used that instead?
    # TODO skip conversion - converting to '%Y%m%dT%H%M%SZ' is because
    #   'PrettyTimeDelegate' expects it
    created_at = arrow.get(version["createdAt"])
    published_time = created_at.strftime("%Y%m%dT%H%M%SZ")
    author = version["author"]
    version_num = version["version"]
    is_hero = version_num < 0

    return VersionItem(
        version_id=version["id"],
        version=version_num,
        is_hero=is_hero,
        subset_id=version["productId"],
        thumbnail_id=version["thumbnailId"],
        published_time=published_time,
        author=author,
        frame_range=frame_range,
        duration=duration,
        handles=handles,
        step=step,
        in_scene=None,
    )


def product_item_from_entity(
    product_entity,
    version_entities,
    product_type_items_by_name,
    folder_label,
):
    product_attribs = product_entity["attrib"]
    group = product_attribs.get("productGroup")
    product_type = product_entity["productType"]
    product_type_item = product_type_items_by_name[product_type]
    product_type_icon = product_type_item.icon

    product_icon = {
        "type": "awesome-font",
        "name": "fa.file-o",
        "color": get_default_entity_icon_color(),
    }
    version_items = [
        version_item_from_entity(version_entity)
        for version_entity in version_entities
    ]

    return ProductItem(
        product_id=product_entity["id"],
        product_type=product_type,
        product_name=product_entity["name"],
        product_icon=product_icon,
        product_type_icon=product_type_icon,
        group_name=group,
        folder_id=product_entity["folderId"],
        folder_label=folder_label,
        version_items=version_items,
    )


def product_type_item_from_data(product_type_data):
    # TODO implement icon implementation
    # icon = product_type_data["icon"]
    # color = product_type_data["color"]
    icon = {
        "type": "awesome-font",
        "name": "fa.folder",
        "color": "#0091B2",
    }
    # TODO implement checked logic
    return ProductTypeItem(product_type_data["name"], icon, True)


class RepreItem:
    def __init__(self, repre_id, version_id):
        self.repre_id = repre_id
        self.version_id = version_id

    @classmethod
    def from_doc(cls, repre_doc):
        return cls(
            str(repre_doc["_id"]),
            str(repre_doc["parent"]),
        )


class ProductsModel:
    def __init__(self, controller):
        self._controller = controller

        self._product_type_items_cache = NestedCacheItem(
            levels=1, default_factory=list)
        self._product_items_cache = NestedCacheItem(
            levels=2, default_factory=dict)
        self._repre_items_cache = NestedCacheItem(
            levels=3, default_factory=dict)

    def reset(self):
        self._product_items_cache.reset()
        self._repre_items_cache.reset()

    def get_product_type_items(self, project_name):
        cache = self._product_type_items_cache[project_name]
        if not cache.is_valid:
            product_types = ayon_api.get_project_product_types(project_name)
            cache.update_data([
                product_type_item_from_data(product_type)
                for product_type in product_types
            ])
        return cache.get_data()

    def get_product_items(self, project_name, folder_ids, sender):
        if not project_name or not folder_ids:
            return []

        project_cache = self._product_items_cache[project_name]
        caches = []
        folder_ids_to_update = set()
        for folder_id in folder_ids:
            cache = project_cache[folder_id]
            caches.append(cache)
            if not cache.is_valid:
                folder_ids_to_update.add(folder_id)

        self._refresh_product_items(
            project_name, folder_ids_to_update, sender)

        output = []
        for cache in caches:
            output.extend(cache.get_data().values())
        return output

    def get_repre_items(self, project_name, version_ids):
        output = {}
        if not version_ids:
            return output
        repre_ids_cache = self._repre_items_cache.get(project_name)
        if repre_ids_cache is None:
            return output

        for version_id in version_ids:
            data = repre_ids_cache[version_id].get_data()
            if data:
                output.update(data)
        return output

    def _refresh_product_items(self, project_name, folder_ids, sender):
        if not project_name or not folder_ids:
            return

        product_type_items = self.get_product_type_items(project_name)
        product_type_items_by_name = {
            product_type_item.name: product_type_item
            for product_type_item in product_type_items
        }
        with self._product_refresh_event_manager(
            project_name, folder_ids, sender
        ):
            folder_items = self._controller.get_folder_items(project_name)
            items_by_folder_id = {
                folder_id: {}
                for folder_id in folder_ids
            }
            products = list(ayon_api.get_products(
                project_name, folder_ids=folder_ids
            ))
            product_ids = {product["id"] for product in products}
            versions = ayon_api.get_versions(
                project_name, product_ids=product_ids)

            versions_by_product_id = collections.defaultdict(list)
            for version in versions:
                versions_by_product_id[version["productId"]].append(version)

            for product in products:
                product_id = product["id"]
                folder_id = product["folderId"]
                folder_item = folder_items.get(folder_id)
                if not folder_item:
                    continue
                versions = versions_by_product_id[product_id]
                if not versions:
                    continue
                product_item = product_item_from_entity(
                    product,
                    versions,
                    product_type_items_by_name,
                    folder_item.label,
                )
                items_by_folder_id[product_item.folder_id][product_id] = (
                    product_item
                )

            project_cache = self._product_items_cache[project_name]
            for folder_id, product_items in items_by_folder_id.items():
                project_cache[folder_id].update_data(product_items)

    @contextlib.contextmanager
    def _product_refresh_event_manager(
        self, project_name, folder_ids, sender
    ):
        self._controller.emit_event(
            "products.refresh.started",
            {
                "project_name": project_name,
                "sender": sender,
                "folder_ids": folder_ids,
            },
            PRODUCTS_MODEL_SENDER
        )
        try:
            yield

        finally:
            self._controller.emit_event(
                "products.refresh.finished",
                {
                    "project_name": project_name,
                    "sender": sender,
                    "folder_ids": folder_ids,
                },
                PRODUCTS_MODEL_SENDER
            )

    def refresh_representations(self, project_name, version_ids):
        self._controller.event_system.emit(
            "model.representations.refresh.started",
            {
                "project_name": project_name,
                "version_ids": version_ids,
            },
            "products.model"
        )
        failed = False
        try:
            self._refresh_representations(project_name, version_ids)
        except Exception:
            failed = True

        self._controller.event_system.emit(
            "model.representations.refresh.finished",
            {
                "project_name": project_name,
                "version_ids": version_ids,
                "failed": failed,
            },
            "products.model"
        )

    def _refresh_representations(self, project_name, version_ids):
        pass
        # if project_name not in self._repre_items_cache:
        #     self._repre_items_cache[project_name] = (
        #         collections.defaultdict(CacheItem.create_outdated)
        #     )
        #
        # version_ids_to_query = set()
        # repre_cache = self._repre_items_cache[project_name]
        # for version_id in version_ids:
        #     if repre_cache[version_id].is_outdated:
        #         version_ids_to_query.add(version_id)
        #
        # if not version_ids_to_query:
        #     return
        #
        # repre_entities_by_version_id = {
        #     version_id: {}
        #     for version_id in version_ids_to_query
        # }
        # repre_entities = ayon_api.get_representations(
        #     project_name, version_ids=version_ids_to_query
        # )
        # for repre_entity in repre_entities:
        #     repre_item = RepreItem.from_doc(repre_entity)
        #     repre_entities_by_version_id[repre_item.version_id][repre_item.id] = {
        #         repre_item
        #     }
        #
        # for version_id, repre_items in repre_docs_by_version_id.items():
        #     repre_cache[version_id].update_data(repre_items)
