
from Qt import QtWidgets


class SimpleLinkView(QtWidgets.QWidget):

    def __init__(self, dbcon, parent=None):
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

    def clear(self):
        self._in_view.clear()
        self._out_view.clear()

    def set_version(self, version_doc):
        self.clear()
        if not version_doc or not self.isVisible():
            return

        # inputs
        #
        for link in version_doc["data"].get("inputLinks", []):
            # Backwards compatibility for "input" key used as "id"
            if "id" not in link:
                link_id = link["input"]
            else:
                link_id = link["id"]
            version = self.dbcon.find_one(
                {"_id": link_id, "type": "version"},
                projection={"name": 1, "parent": 1}
            )
            if not version:
                continue
            subset = self.dbcon.find_one(
                {"_id": version["parent"], "type": "subset"},
                projection={"name": 1, "parent": 1}
            )
            if not subset:
                continue
            asset = self.dbcon.find_one(
                {"_id": subset["parent"], "type": "asset"},
                projection={"name": 1}
            )

            self._in_view.addItem("{asset} {subset} v{version:0>3}".format(
                asset=asset["name"],
                subset=subset["name"],
                version=version["name"],
            ))

        # outputs
        #
        outputs = self.dbcon.find(
            {"type": "version", "data.inputLinks.input": version_doc["_id"]},
            projection={"name": 1, "parent": 1}
        )
        for version in outputs or []:
            subset = self.dbcon.find_one(
                {"_id": version["parent"], "type": "subset"},
                projection={"name": 1, "parent": 1}
            )
            if not subset:
                continue
            asset = self.dbcon.find_one(
                {"_id": subset["parent"], "type": "asset"},
                projection={"name": 1}
            )

            self._out_view.addItem("{asset} {subset} v{version:0>3}".format(
                asset=asset["name"],
                subset=subset["name"],
                version=version["name"],
            ))
