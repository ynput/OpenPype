import collections
import contextlib

import arrow
import ayon_api
from ayon_api.operations import OperationsSession

from openpype.style import get_default_entity_icon_color
from openpype.tools.ayon_utils.models import NestedCacheItem
from openpype.tools.ayon_loader.abstract import (
    ProductTypeItem,
    ProductItem,
    VersionItem,
    RepreItem,
)

PRODUCTS_MODEL_SENDER = "products.model"


def version_item_from_entity(version):
    version_attribs = version["attrib"]
    frame_start = version_attribs.get("frameStart")
    frame_end = version_attribs.get("frameEnd")
    handle_start = version_attribs.get("handleStart")
    handle_end = version_attribs.get("handleEnd")
    step = version_attribs.get("step")
    comment = version_attribs.get("comment")
    source = version_attribs.get("source")

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
        product_id=version["productId"],
        thumbnail_id=version["thumbnailId"],
        published_time=published_time,
        author=author,
        frame_range=frame_range,
        duration=duration,
        handles=handles,
        step=step,
        comment=comment,
        source=source,
    )


def product_item_from_entity(
    product_entity,
    version_entities,
    product_type_items_by_name,
    folder_label,
    product_in_scene,
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
    version_items = {
        version_entity["id"]: version_item_from_entity(version_entity)
        for version_entity in version_entities
    }

    return ProductItem(
        product_id=product_entity["id"],
        product_type=product_type,
        product_name=product_entity["name"],
        product_icon=product_icon,
        product_type_icon=product_type_icon,
        product_in_scene=product_in_scene,
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


class ProductsModel:
    """Model for products, version and representation.

    All of the entities are product based. This model prepares data for UI
    and caches it for faster access.

    Note:
        Data are not used for actions model because that would require to
            break OpenPype compatibility of 'LoaderPlugin's.
    """

    lifetime = 60  # In seconds (minute by default)

    def __init__(self, controller):
        self._controller = controller

        # Mapping helpers
        # NOTE - mapping must be cleaned up with cache cleanup
        self._product_item_by_id = collections.defaultdict(dict)
        self._version_item_by_id = collections.defaultdict(dict)
        self._product_folder_ids_mapping = collections.defaultdict(dict)

        # Cache helpers
        self._product_type_items_cache = NestedCacheItem(
            levels=1, default_factory=list, lifetime=self.lifetime)
        self._product_items_cache = NestedCacheItem(
            levels=2, default_factory=dict, lifetime=self.lifetime)
        self._repre_items_cache = NestedCacheItem(
            levels=2, default_factory=dict, lifetime=self.lifetime)

    def reset(self):
        """Reset model with all cached data."""

        self._product_item_by_id.clear()
        self._version_item_by_id.clear()
        self._product_folder_ids_mapping.clear()

        self._product_type_items_cache.reset()
        self._product_items_cache.reset()
        self._repre_items_cache.reset()

    def get_product_type_items(self, project_name):
        """Product type items for project.

        Args:
            project_name (str): Project name.

        Returns:
            list[ProductTypeItem]: Product type items.
        """

        cache = self._product_type_items_cache[project_name]
        if not cache.is_valid:
            product_types = ayon_api.get_project_product_types(project_name)
            cache.update_data([
                product_type_item_from_data(product_type)
                for product_type in product_types
            ])
        return cache.get_data()

    def get_product_items(self, project_name, folder_ids, sender):
        """Product items with versions for project and folder ids.

        Product items also contain version items. They're directly connected
        to product items in the UI and the separation is not needed.

        Args:
            project_name (Union[str, None]): Project name.
            folder_ids (Iterable[str]): Folder ids.
            sender (Union[str, None]): Who triggered the method.

        Returns:
            list[ProductItem]: Product items.
        """

        if not project_name or not folder_ids:
            return []

        project_cache = self._product_items_cache[project_name]
        output = []
        folder_ids_to_update = set()
        for folder_id in folder_ids:
            cache = project_cache[folder_id]
            if cache.is_valid:
                output.extend(cache.get_data().values())
            else:
                folder_ids_to_update.add(folder_id)

        self._refresh_product_items(
            project_name, folder_ids_to_update, sender)

        for folder_id in folder_ids_to_update:
            cache = project_cache[folder_id]
            output.extend(cache.get_data().values())
        return output

    def get_product_item(self, project_name, product_id):
        """Get product item based on passed product id.

        This method is using cached items, but if cache is not valid it also
        can query the item.

        Args:
            project_name (Union[str, None]): Where to look for product.
            product_id (Union[str, None]): Product id to receive.

        Returns:
            Union[ProductItem, None]: Product item or 'None' if not found.
        """

        if not any((project_name, product_id)):
            return None

        product_items_by_id = self._product_item_by_id[project_name]
        product_item = product_items_by_id.get(product_id)
        if product_item is not None:
            return product_item
        for product_item in self._query_product_items_by_ids(
            project_name, product_ids=[product_id]
        ).values():
            return product_item

    def get_product_ids_by_repre_ids(self, project_name, repre_ids):
        """Get product ids based on passed representation ids.

        Args:
            project_name (str): Where to look for representations.
            repre_ids (Iterable[str]): Representation ids.

        Returns:
            set[str]: Product ids for passed representation ids.
        """

        # TODO look out how to use single server call
        if not repre_ids:
            return set()
        repres = ayon_api.get_representations(
            project_name, repre_ids, fields=["versionId"]
        )
        version_ids = {repre["versionId"] for repre in repres}
        if not version_ids:
            return set()
        versions = ayon_api.get_versions(
            project_name, version_ids=version_ids, fields=["productId"]
        )
        return {v["productId"] for v in versions}

    def get_repre_items(self, project_name, version_ids, sender):
        """Get representation items for passed version ids.

        Args:
            project_name (str): Project name.
            version_ids (Iterable[str]): Version ids.
            sender (Union[str, None]): Who triggered the method.

        Returns:
            list[RepreItem]: Representation items.
        """

        output = []
        if not any((project_name, version_ids)):
            return output

        invalid_version_ids = set()
        project_cache = self._repre_items_cache[project_name]
        for version_id in version_ids:
            version_cache = project_cache[version_id]
            if version_cache.is_valid:
                output.extend(version_cache.get_data().values())
            else:
                invalid_version_ids.add(version_id)

        if invalid_version_ids:
            self.refresh_representation_items(
                project_name, invalid_version_ids, sender
            )

        for version_id in invalid_version_ids:
            version_cache = project_cache[version_id]
            output.extend(version_cache.get_data().values())

        return output

    def change_products_group(self, project_name, product_ids, group_name):
        """Change group name for passed product ids.

        Group name is stored in 'attrib' of product entity and is used in UI
        to group items.

        Method triggers "products.group.changed" event with data:
            {
                "project_name": project_name,
                "folder_ids": folder_ids,
                "product_ids": product_ids,
                "group_name": group_name
            }

        Args:
            project_name (str): Project name.
            product_ids (Iterable[str]): Product ids to change group name for.
            group_name (str): Group name to set.
        """

        if not product_ids:
            return

        product_items = self._get_product_items_by_id(
            project_name, product_ids
        )
        if not product_items:
            return

        session = OperationsSession()
        folder_ids = set()
        for product_item in product_items.values():
            session.update_entity(
                project_name,
                "product",
                product_item.product_id,
                {"attrib": {"productGroup": group_name}}
            )
            folder_ids.add(product_item.folder_id)
            product_item.group_name = group_name

        session.commit()
        self._controller.emit_event(
            "products.group.changed",
            {
                "project_name": project_name,
                "folder_ids": folder_ids,
                "product_ids": product_ids,
                "group_name": group_name,
            },
            PRODUCTS_MODEL_SENDER
        )

    def _get_product_items_by_id(self, project_name, product_ids):
        product_item_by_id = self._product_item_by_id[project_name]
        missing_product_ids = set()
        output = {}
        for product_id in product_ids:
            product_item = product_item_by_id.get(product_id)
            if product_item is not None:
                output[product_id] = product_item
            else:
                missing_product_ids.add(product_id)

        output.update(
            self._query_product_items_by_ids(
                project_name, missing_product_ids
            )
        )
        return output

    def _get_version_items_by_id(self, project_name, version_ids):
        version_item_by_id = self._version_item_by_id[project_name]
        missing_version_ids = set()
        output = {}
        for version_id in version_ids:
            version_item = version_item_by_id.get(version_id)
            if version_item is not None:
                output[version_id] = version_item
            else:
                missing_version_ids.add(version_id)

        output.update(
            self._query_version_items_by_ids(
                project_name, missing_version_ids
            )
        )
        return output

    def _create_product_items(
        self,
        project_name,
        products,
        versions,
        folder_items=None,
        product_type_items=None,
    ):
        if folder_items is None:
            folder_items = self._controller.get_folder_items(project_name)

        if product_type_items is None:
            product_type_items = self.get_product_type_items(project_name)

        loaded_product_ids = self._controller.get_loaded_product_ids()

        versions_by_product_id = collections.defaultdict(list)
        for version in versions:
            versions_by_product_id[version["productId"]].append(version)
        product_type_items_by_name = {
            product_type_item.name: product_type_item
            for product_type_item in product_type_items
        }
        output = {}
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
                product_id in loaded_product_ids,
            )
            output[product_id] = product_item
        return output

    def _query_product_items_by_ids(
        self,
        project_name,
        folder_ids=None,
        product_ids=None,
        folder_items=None
    ):
        """Query product items.

        This method does get from, or store to, cache attributes.

        One of 'product_ids' or 'folder_ids' must be passed to the method.

        Args:
            project_name (str): Project name.
            folder_ids (Optional[Iterable[str]]): Folder ids under which are
                products.
            product_ids (Optional[Iterable[str]]): Product ids to use.
            folder_items (Optional[Dict[str, FolderItem]]): Prepared folder
                items from controller.

        Returns:
            dict[str, ProductItem]: Product items by product id.
        """

        if not folder_ids and not product_ids:
            return {}

        kwargs = {}
        if folder_ids is not None:
            kwargs["folder_ids"] = folder_ids

        if product_ids is not None:
            kwargs["product_ids"] = product_ids

        products = list(ayon_api.get_products(project_name, **kwargs))
        product_ids = {product["id"] for product in products}

        versions = ayon_api.get_versions(
            project_name, product_ids=product_ids
        )

        return self._create_product_items(
            project_name, products, versions, folder_items=folder_items
        )

    def _query_version_items_by_ids(self, project_name, version_ids):
        versions = list(ayon_api.get_versions(
            project_name, version_ids=version_ids
        ))
        product_ids = {version["productId"] for version in versions}
        products = list(ayon_api.get_products(
            project_name, product_ids=product_ids
        ))
        product_items = self._create_product_items(
            project_name, products, versions
        )
        version_items = {}
        for product_item in product_items.values():
            version_items.update(product_item.version_items)
        return version_items

    def _clear_product_version_items(self, project_name, folder_ids):
        """Clear product and version items from memory.

        When products are re-queried for a folders, the old product and version
        items in '_product_item_by_id' and '_version_item_by_id' should
        be cleaned up from memory. And mapping in stored in
        '_product_folder_ids_mapping' is not relevant either.

        Args:
            project_name (str): Name of project.
            folder_ids (Iterable[str]): Folder ids which are being refreshed.
        """

        project_mapping = self._product_folder_ids_mapping[project_name]
        if not project_mapping:
            return

        product_item_by_id = self._product_item_by_id[project_name]
        version_item_by_id = self._version_item_by_id[project_name]
        for folder_id in folder_ids:
            product_ids = project_mapping.pop(folder_id, None)
            if not product_ids:
                continue

            for product_id in product_ids:
                product_item = product_item_by_id.pop(product_id, None)
                if product_item is None:
                    continue
                for version_item in product_item.version_items.values():
                    version_item_by_id.pop(version_item.version_id, None)

    def _refresh_product_items(self, project_name, folder_ids, sender):
        """Refresh product items and store them in cache.

        Args:
            project_name (str): Name of project.
            folder_ids (Iterable[str]): Folder ids which are being refreshed.
            sender (Union[str, None]): Who triggered the refresh.
        """

        if not project_name or not folder_ids:
            return

        self._clear_product_version_items(project_name, folder_ids)

        project_mapping = self._product_folder_ids_mapping[project_name]
        product_item_by_id = self._product_item_by_id[project_name]
        version_item_by_id = self._version_item_by_id[project_name]

        for folder_id in folder_ids:
            project_mapping[folder_id] = set()

        with self._product_refresh_event_manager(
            project_name, folder_ids, sender
        ):
            folder_items = self._controller.get_folder_items(project_name)
            items_by_folder_id = {
                folder_id: {}
                for folder_id in folder_ids
            }
            product_items_by_id = self._query_product_items_by_ids(
                project_name,
                folder_ids=folder_ids,
                folder_items=folder_items
            )
            for product_id, product_item in product_items_by_id.items():
                folder_id = product_item.folder_id
                items_by_folder_id[product_item.folder_id][product_id] = (
                    product_item
                )

                project_mapping[folder_id].add(product_id)
                product_item_by_id[product_id] = product_item
                for version_id, version_item in (
                    product_item.version_items.items()
                ):
                    version_item_by_id[version_id] = version_item

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
                "folder_ids": folder_ids,
                "sender": sender,
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
                    "folder_ids": folder_ids,
                    "sender": sender,
                },
                PRODUCTS_MODEL_SENDER
            )

    def refresh_representation_items(
        self, project_name, version_ids, sender
    ):
        if not any((project_name, version_ids)):
            return
        self._controller.emit_event(
            "model.representations.refresh.started",
            {
                "project_name": project_name,
                "version_ids": version_ids,
                "sender": sender,
            },
            PRODUCTS_MODEL_SENDER
        )
        failed = False
        try:
            self._refresh_representation_items(project_name, version_ids)
        except Exception:
            # TODO add more information about failed refresh
            failed = True

        self._controller.emit_event(
            "model.representations.refresh.finished",
            {
                "project_name": project_name,
                "version_ids": version_ids,
                "sender": sender,
                "failed": failed,
            },
            PRODUCTS_MODEL_SENDER
        )

    def _refresh_representation_items(self, project_name, version_ids):
        representations = list(ayon_api.get_representations(
            project_name,
            version_ids=version_ids,
            fields=["id", "name", "versionId"]
        ))

        version_items_by_id = self._get_version_items_by_id(
            project_name, version_ids
        )
        product_ids = {
            version_item.product_id
            for version_item in version_items_by_id.values()
        }
        product_items_by_id = self._get_product_items_by_id(
            project_name, product_ids
        )
        repre_icon = {
            "type": "awesome-font",
            "name": "fa.file-o",
            "color": get_default_entity_icon_color(),
        }
        repre_items_by_version_id = collections.defaultdict(dict)
        for representation in representations:
            version_id = representation["versionId"]
            version_item = version_items_by_id.get(version_id)
            if version_item is None:
                continue
            product_item = product_items_by_id.get(version_item.product_id)
            if product_item is None:
                continue
            repre_id = representation["id"]
            repre_item = RepreItem(
                repre_id,
                representation["name"],
                repre_icon,
                product_item.product_name,
                product_item.folder_label,
            )
            repre_items_by_version_id[version_id][repre_id] = repre_item

        project_cache = self._repre_items_cache[project_name]
        for version_id, repre_items in repre_items_by_version_id.items():
            version_cache = project_cache[version_id]
            version_cache.update_data(repre_items)
