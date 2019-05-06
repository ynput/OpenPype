from . import QtCore, QtGui, QtWidgets


class ComponentsList(QtWidgets.QTableWidget):
    def __init__(self, parent=None):
        super().__init__(parent=parent)

        self._main_column = 0

        self.setColumnCount(1)
        self.setSelectionBehavior(
            QtWidgets.QAbstractItemView.SelectRows
        )
        self.setSelectionMode(
            QtWidgets.QAbstractItemView.ExtendedSelection
        )
        self.setVerticalScrollMode(
            QtWidgets.QAbstractItemView.ScrollPerPixel
        )
        self.verticalHeader().hide()

        try:
            self.verticalHeader().setResizeMode(
                QtWidgets.QHeaderView.ResizeToContents
            )
        except Exception:
            self.verticalHeader().setSectionResizeMode(
                QtWidgets.QHeaderView.ResizeToContents
            )

        self.horizontalHeader().setStretchLastSection(True)
        self.horizontalHeader().hide()

    def count(self):
        return self.rowCount()

    def add_widget(self, widget, row=None):
        if row is None:
            row = self.count()

        self.insertRow(row)
        self.setCellWidget(row, self._main_column, widget)

        self.resizeRowToContents(row)

        return row

    def remove_widget(self, row):
        self.removeRow(row)

    def move_widget(self, widget, newRow):
        oldRow = self.indexOfWidget(widget)
        if oldRow:
            self.insertRow(newRow)
            # Collect the oldRow after insert to make sure we move the correct
            # widget.
            oldRow = self.indexOfWidget(widget)

            self.setCellWidget(newRow, self._main_column, widget)
            self.resizeRowToContents(oldRow)

            # Remove the old row
            self.removeRow(oldRow)

    def clear_widgets(self):
        '''Remove all widgets.'''
        self.clear()
        self.setRowCount(0)

    def widget_index(self, widget):
        index = None
        for row in range(self.count()):
            candidateWidget = self.widget_at(row)
            if candidateWidget == widget:
                index = row
                break

        return index

    def widgets(self):
        widgets = []
        for row in range(self.count()):
            widget = self.widget_at(row)
            widgets.append(widget)

        return widgets

    def widget_at(self, row):
        return self.cellWidget(row, self._main_column)
