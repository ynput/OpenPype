import collections
from openpype.client import (
    get_versions,
    get_subsets,
    get_assets,
    get_version_links,
)

from Qt import QtWidgets


class SimpleLinkView(QtWidgets.QWidget):
    def __init__(self, dbcon, parent):
        super(SimpleLinkView, self).__init__(parent=parent)
        self.dbcon = dbcon

        # TODO: display selected target

        in_text = QtWidgets.QLabel("Inputs")
        in_view = QtWidgets.QListWidget(parent=self)
        out_text = QtWidgets.QLabel("Outputs")
        out_view = QtWidgets.QListWidget(parent=self)

        layout = QtWidgets.QGridLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(in_text, 0, 0)
        layout.addWidget(in_view, 1, 0)
        layout.addWidget(out_text, 0, 1)
        layout.addWidget(out_view, 1, 1)

        self._in_view = in_view
        self._out_view = out_view
        self._version_doc_to_process = None

    @property
    def project_name(self):
        return self.dbcon.current_project()

    def clear(self):
        self._in_view.clear()
        self._out_view.clear()

    def set_version(self, version_doc):
        self.clear()
        self._version_doc_to_process = version_doc
        if version_doc and self.isVisible():
            self._fill_values()

    def showEvent(self, event):
        super(SimpleLinkView, self).showEvent(event)
        self._fill_values()

    def _fill_values(self):
        if self._version_doc_to_process is None:
            return
        version_doc = self._version_doc_to_process
        self._version_doc_to_process = None
        self._fill_inputs(version_doc)
        self._fill_outputs(version_doc)

    def _fill_inputs(self, version_doc):
        version_ids = set()
        for link in version_doc["data"].get("inputLinks", []):
            # Backwards compatibility for "input" key used as "id"
            if "id" not in link:
                link_id = link["input"]
            else:
                link_id = link["id"]
            version_ids.add(link_id)

        version_docs = list(get_versions(
            self.project_name,
            version_ids=version_ids,
            fields=["name", "parent"]
        ))

        subset_docs = []
        versions_by_subset_id = collections.defaultdict(list)
        if versions_by_subset_id:
            for version_doc in version_docs:
                subset_id = version_doc["parent"]
                versions_by_subset_id[subset_id].append(version_doc)

            subset_docs = list(get_subsets(
                self.project_name,
                subset_ids=versions_by_subset_id.keys(),
                fields=["_id", "name", "parent"]
            ))

        asset_docs = []
        subsets_by_asset_id = collections.defaultdict(list)
        if subset_docs:
            for subset_doc in subset_docs:
                asset_id = subset_doc["parent"]
                subsets_by_asset_id[asset_id].append(subset_doc)

            asset_docs = list(get_assets(
                self.project_name,
                asset_ids=subsets_by_asset_id.keys(),
                fields=["_id", "name"]
            ))

        for asset_doc in asset_docs:
            asset_id = asset_doc["_id"]
            for subset_doc in subsets_by_asset_id[asset_id]:
                subset_id = subset_doc["_id"]
                for version_doc in versions_by_subset_id[subset_id]:
                    self._in_view.addItem("{} {} v{:0>3}".format(
                        asset_doc["name"],
                        subset_doc["name"],
                        version_doc["name"],
                    ))

    def _fill_outputs(self, version_doc):
        version_docs = list(get_version_links(
            self.project_name,
            version_doc["_id"],
            fields=["name", "parent"]
        ))
        subset_docs = []
        versions_by_subset_id = collections.defaultdict(list)
        if versions_by_subset_id:
            for version_doc in version_docs:
                subset_id = version_doc["parent"]
                versions_by_subset_id[subset_id].append(version_doc)

            subset_docs = list(get_subsets(
                self.project_name,
                subset_ids=versions_by_subset_id.keys(),
                fields=["_id", "name", "parent"]
            ))

        asset_docs = []
        subsets_by_asset_id = collections.defaultdict(list)
        if subset_docs:
            for subset_doc in subset_docs:
                asset_id = subset_doc["parent"]
                subsets_by_asset_id[asset_id].append(subset_doc)

            asset_docs = list(get_assets(
                self.project_name,
                asset_ids=subsets_by_asset_id.keys(),
                fields=["_id", "name"]
            ))

        for asset_doc in asset_docs:
            asset_id = asset_doc["_id"]
            for subset_doc in subsets_by_asset_id[asset_id]:
                subset_id = subset_doc["_id"]
                for version_doc in versions_by_subset_id[subset_id]:
                    self._out_view.addItem("{} {} v{:0>3}".format(
                        asset_doc["name"],
                        subset_doc["name"],
                        version_doc["name"],
                    ))
