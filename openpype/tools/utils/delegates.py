import time
from datetime import datetime
import logging
import numbers

import Qt
from Qt import QtWidgets, QtGui, QtCore

if Qt.__binding__ == "PySide":
    from PySide.QtGui import QStyleOptionViewItemV4
elif Qt.__binding__ == "PyQt4":
    from PyQt4.QtGui import QStyleOptionViewItemV4

from openpype.client import (
    get_versions,
    get_hero_versions,
)
from openpype.pipeline import HeroVersionType
from .models import TreeModel
from . import lib

log = logging.getLogger(__name__)


class VersionDelegate(QtWidgets.QStyledItemDelegate):
    """A delegate that display version integer formatted as version string."""

    version_changed = QtCore.Signal()
    first_run = False
    lock = False

    def __init__(self, dbcon, *args, **kwargs):
        self.dbcon = dbcon
        super(VersionDelegate, self).__init__(*args, **kwargs)

    def displayText(self, value, locale):
        if isinstance(value, HeroVersionType):
            return lib.format_version(value, True)
        assert isinstance(value, numbers.Integral), (
            "Version is not integer. \"{}\" {}".format(value, str(type(value)))
        )
        return lib.format_version(value)

    def paint(self, painter, option, index):
        fg_color = index.data(QtCore.Qt.ForegroundRole)
        if fg_color:
            if isinstance(fg_color, QtGui.QBrush):
                fg_color = fg_color.color()
            elif isinstance(fg_color, QtGui.QColor):
                pass
            else:
                fg_color = None

        if not fg_color:
            return super(VersionDelegate, self).paint(painter, option, index)

        if option.widget:
            style = option.widget.style()
        else:
            style = QtWidgets.QApplication.style()

        style.drawControl(
            style.CE_ItemViewItem, option, painter, option.widget
        )

        painter.save()

        text = self.displayText(
            index.data(QtCore.Qt.DisplayRole), option.locale
        )
        pen = painter.pen()
        pen.setColor(fg_color)
        painter.setPen(pen)

        text_rect = style.subElementRect(style.SE_ItemViewItemText, option)
        text_margin = style.proxy().pixelMetric(
            style.PM_FocusFrameHMargin, option, option.widget
        ) + 1

        painter.drawText(
            text_rect.adjusted(text_margin, 0, - text_margin, 0),
            option.displayAlignment,
            text
        )

        painter.restore()

    def createEditor(self, parent, option, index):
        item = index.data(TreeModel.ItemRole)
        if item.get("isGroup") or item.get("isMerged"):
            return

        editor = QtWidgets.QComboBox(parent)

        def commit_data():
            if not self.first_run:
                self.commitData.emit(editor)  # Update model data
                self.version_changed.emit()   # Display model data
        editor.currentIndexChanged.connect(commit_data)

        self.first_run = True
        self.lock = False

        return editor

    def setEditorData(self, editor, index):
        if self.lock:
            # Only set editor data once per delegation
            return

        editor.clear()

        # Current value of the index
        item = index.data(TreeModel.ItemRole)
        value = index.data(QtCore.Qt.DisplayRole)
        if item["version_document"]["type"] != "hero_version":
            assert isinstance(value, numbers.Integral), (
                "Version is not integer"
            )

        project_name = self.dbcon.active_project()
        # Add all available versions to the editor
        parent_id = item["version_document"]["parent"]
        version_docs = list(sorted(
            get_versions(project_name, subset_ids=[parent_id]),
            key=lambda item: item["name"]
        ))

        hero_versions = list(
            get_hero_versions(
                project_name,
                subset_ids=[parent_id],
                fields=["name", "data.tags", "version_id"]
            )
        )
        hero_version_doc = None
        if hero_versions:
            hero_version_doc = hero_versions[0]

        doc_for_hero_version = None

        selected = None
        items = []
        for version_doc in version_docs:
            version_tags = version_doc["data"].get("tags") or []
            if "deleted" in version_tags:
                continue

            if (
                hero_version_doc
                and doc_for_hero_version is None
                and hero_version_doc["version_id"] == version_doc["_id"]
            ):
                doc_for_hero_version = version_doc

            label = lib.format_version(version_doc["name"])
            item = QtGui.QStandardItem(label)
            item.setData(version_doc, QtCore.Qt.UserRole)
            items.append(item)

            if version_doc["name"] == value:
                selected = item

        if hero_version_doc and doc_for_hero_version:
            version_name = doc_for_hero_version["name"]
            label = lib.format_version(version_name, True)
            if isinstance(value, HeroVersionType):
                index = len(version_docs)
            hero_version_doc["name"] = HeroVersionType(version_name)

            item = QtGui.QStandardItem(label)
            item.setData(hero_version_doc, QtCore.Qt.UserRole)
            items.append(item)

        # Reverse items so latest versions be upper
        items = list(reversed(items))
        for item in items:
            editor.model().appendRow(item)

        index = 0
        if selected:
            index = selected.row()

        # Will trigger index-change signal
        editor.setCurrentIndex(index)
        self.first_run = False
        self.lock = True

    def setModelData(self, editor, model, index):
        """Apply the integer version back in the model"""
        version = editor.itemData(editor.currentIndex())
        model.setData(index, version["name"])


def pretty_date(t, now=None, strftime="%b %d %Y %H:%M"):
    """Parse datetime to readable timestamp

    Within first ten seconds:
        - "just now",
    Within first minute ago:
        - "%S seconds ago"
    Within one hour ago:
        - "%M minutes ago".
    Within one day ago:
        - "%H:%M hours ago"
    Else:
        "%Y-%m-%d %H:%M:%S"

    """

    assert isinstance(t, datetime)
    if now is None:
        now = datetime.now()
    assert isinstance(now, datetime)
    diff = now - t

    second_diff = diff.seconds
    day_diff = diff.days

    # future (consider as just now)
    if day_diff < 0:
        return "just now"

    # history
    if day_diff == 0:
        if second_diff < 10:
            return "just now"
        if second_diff < 60:
            return str(second_diff) + " seconds ago"
        if second_diff < 120:
            return "a minute ago"
        if second_diff < 3600:
            return str(second_diff // 60) + " minutes ago"
        if second_diff < 86400:
            minutes = (second_diff % 3600) // 60
            hours = second_diff // 3600
            return "{0}:{1:02d} hours ago".format(hours, minutes)

    return t.strftime(strftime)


def pretty_timestamp(t, now=None):
    """Parse timestamp to user readable format

    >>> pretty_timestamp("20170614T151122Z", now="20170614T151123Z")
    'just now'

    >>> pretty_timestamp("20170614T151122Z", now="20170614T171222Z")
    '2:01 hours ago'

    Args:
        t (str): The time string to parse.
        now (str, optional)

    Returns:
        str: human readable "recent" date.

    """

    if now is not None:
        try:
            now = time.strptime(now, "%Y%m%dT%H%M%SZ")
            now = datetime.fromtimestamp(time.mktime(now))
        except ValueError as e:
            log.warning("Can't parse 'now' time format: {0} {1}".format(t, e))
            return None

    if isinstance(t, float):
        dt = datetime.fromtimestamp(t)
    else:
        # Parse the time format as if it is `str` result from
        # `pyblish.lib.time()` which usually is stored in Avalon database.
        try:
            t = time.strptime(t, "%Y%m%dT%H%M%SZ")
        except ValueError as e:
            log.warning("Can't parse time format: {0} {1}".format(t, e))
            return None
        dt = datetime.fromtimestamp(time.mktime(t))

    # prettify
    return pretty_date(dt, now=now)


class PrettyTimeDelegate(QtWidgets.QStyledItemDelegate):
    """A delegate that displays a timestamp as a pretty date.

    This displays dates like `pretty_date`.

    """

    def displayText(self, value, locale):
        if value is not None:
            return pretty_timestamp(value)
