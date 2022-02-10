"""
This based on the flickcharm-python code from:
    https://code.google.com/archive/p/flickcharm-python/

Which states:
    This is a Python (PyQt) port of Ariya Hidayat's elegant FlickCharm
    hack which adds kinetic scrolling to any scrollable Qt widget.

    Licensed under GNU GPL version 2 or later.

It has been altered to fix edge cases where clicks and drags would not
propagate correctly under some conditions. It also allows a small "dead zone"
threshold in which it will still propagate the user pressed click if he or she
travelled only very slightly with the cursor.

"""

import copy
from Qt import QtWidgets, QtCore, QtGui


class FlickData(object):
    Steady = 0
    Pressed = 1
    ManualScroll = 2
    AutoScroll = 3
    Stop = 4

    def __init__(self):
        self.state = FlickData.Steady
        self.widget = None
        self.pressPos = QtCore.QPoint(0, 0)
        self.offset = QtCore.QPoint(0, 0)
        self.dragPos = QtCore.QPoint(0, 0)
        self.speed = QtCore.QPoint(0, 0)
        self.travelled = 0
        self.ignored = []


class FlickCharm(QtCore.QObject):
    """Make scrollable widgets flickable.

    For example:
        charm = FlickCharm()
        charm.activateOn(widget)

    It can `activateOn` multiple widgets with a single FlickCharm instance.
    Be aware that the FlickCharm object must be kept around for it not
    to get garbage collected and losing the flickable behavior.

    Flick away!

    """

    def __init__(self, parent=None):
        super(FlickCharm, self).__init__(parent=parent)

        self.flickData = {}
        self.ticker = QtCore.QBasicTimer()

        # The flick button to use
        self.button = QtCore.Qt.LeftButton

        # The time taken per update tick of flicking behavior
        self.tick_time = 20

        # Allow a item click/press directly when AutoScroll is slower than
        # this threshold velocity
        self.click_in_autoscroll_threshold = 10

        # Allow an item click/press to propagate as opposed to scrolling
        # when the cursor travelled less than this amount of pixels
        # Note: back & forth motion increases the value too
        self.travel_threshold = 20

        self.max_speed = 64  # max scroll speed
        self.drag = 1  # higher drag will stop autoscroll faster

    def activateOn(self, widget):
        viewport = widget.viewport()
        viewport.installEventFilter(self)
        widget.installEventFilter(self)
        self.flickData[viewport] = FlickData()
        self.flickData[viewport].widget = widget
        self.flickData[viewport].state = FlickData.Steady

    def deactivateFrom(self, widget):

        viewport = widget.viewport()
        viewport.removeEventFilter(self)
        widget.removeEventFilter(self)
        self.flickData.pop(viewport)

    def eventFilter(self, obj, event):

        if not obj.isWidgetType():
            return False

        eventType = event.type()
        if eventType != QtCore.QEvent.MouseButtonPress and \
                eventType != QtCore.QEvent.MouseButtonRelease and \
                eventType != QtCore.QEvent.MouseMove:
            return False

        if event.modifiers() != QtCore.Qt.NoModifier:
            return False

        if obj not in self.flickData:
            return False

        data = self.flickData[obj]
        found, newIgnored = removeAll(data.ignored, event)
        if found:
            data.ignored = newIgnored
            return False

        if data.state == FlickData.Steady:
            if eventType == QtCore.QEvent.MouseButtonPress:
                if event.buttons() == self.button:
                    self._set_press_pos_and_offset(event, data)
                    data.state = FlickData.Pressed
                    return True

        elif data.state == FlickData.Pressed:
            if eventType == QtCore.QEvent.MouseButtonRelease:
                # User didn't actually scroll but clicked in
                # the widget. Let the original press and release
                # event be evaluated on the Widget
                data.state = FlickData.Steady
                event1 = QtGui.QMouseEvent(QtCore.QEvent.MouseButtonPress,
                                           data.pressPos,
                                           QtCore.Qt.LeftButton,
                                           QtCore.Qt.LeftButton,
                                           QtCore.Qt.NoModifier)
                # Copy the current event
                event2 = QtGui.QMouseEvent(QtCore.QEvent.MouseButtonRelease,
                                           event.pos(),
                                           event.button(),
                                           event.buttons(),
                                           event.modifiers())
                data.ignored.append(event1)
                data.ignored.append(event2)
                QtWidgets.QApplication.postEvent(obj, event1)
                QtWidgets.QApplication.postEvent(obj, event2)
                return True
            elif eventType == QtCore.QEvent.MouseMove:
                data.state = FlickData.ManualScroll
                data.dragPos = QtGui.QCursor.pos()
                if not self.ticker.isActive():
                    self.ticker.start(self.tick_time, self)
                return True

        elif data.state == FlickData.ManualScroll:
            if eventType == QtCore.QEvent.MouseMove:
                pos = event.pos()
                delta = pos - data.pressPos
                data.travelled += delta.manhattanLength()
                setScrollOffset(data.widget, data.offset - delta)
                return True
            elif eventType == QtCore.QEvent.MouseButtonRelease:

                if data.travelled <= self.travel_threshold:
                    # If the user travelled less than the threshold
                    # don't go into autoscroll mode but assume the user
                    # intended to click instead
                    return self._propagate_click(obj, event, data)

                data.state = FlickData.AutoScroll
                return True

        elif data.state == FlickData.AutoScroll:
            if eventType == QtCore.QEvent.MouseButtonPress:

                # Allow pressing when auto scroll is already slower than
                # the click in autoscroll threshold
                velocity = data.speed.manhattanLength()
                if velocity <= self.click_in_autoscroll_threshold:
                    self._set_press_pos_and_offset(event, data)
                    data.state = FlickData.Pressed
                else:
                    data.state = FlickData.Stop

                data.speed = QtCore.QPoint(0, 0)
                return True
            elif eventType == QtCore.QEvent.MouseButtonRelease:
                data.state = FlickData.Steady
                data.speed = QtCore.QPoint(0, 0)
                return True

        elif data.state == FlickData.Stop:
            if eventType == QtCore.QEvent.MouseButtonRelease:
                data.state = FlickData.Steady

                # If the user had a very limited scroll smaller than the
                # threshold consider it a regular press and release.
                if data.travelled < self.travel_threshold:
                    return self._propagate_click(obj, event, data)

                return True
            elif eventType == QtCore.QEvent.MouseMove:
                # Reset the press position and offset to allow us to "continue"
                # the scroll from the new point the user clicked and then held
                # down to continue scrolling after AutoScroll.
                self._set_press_pos_and_offset(event, data)
                data.state = FlickData.ManualScroll

                data.dragPos = QtGui.QCursor.pos()
                if not self.ticker.isActive():
                    self.ticker.start(self.tick_time, self)
                return True

        return False

    def _set_press_pos_and_offset(self, event, data):
        """Store current event position on Press"""
        data.state = FlickData.Pressed
        data.pressPos = copy.copy(event.pos())
        data.offset = scrollOffset(data.widget)
        data.travelled = 0

    def _propagate_click(self, obj, event, data):
        """Propagate from Pressed state with MouseButtonRelease event.

        Use only on button release in certain states to propagate a click,
        for example when the user dragged only a slight distance under the
        travel threshold.

        """

        data.state = FlickData.Pressed
        data.pressPos = copy.copy(event.pos())
        data.offset = scrollOffset(data.widget)
        data.travelled = 0
        self.eventFilter(obj, event)
        return True

    def timerEvent(self, event):

        count = 0
        for data in self.flickData.values():
            if data.state == FlickData.ManualScroll:
                count += 1
                cursorPos = QtGui.QCursor.pos()
                data.speed = cursorPos - data.dragPos
                data.dragPos = cursorPos
            elif data.state == FlickData.AutoScroll:
                count += 1
                data.speed = deaccelerate(data.speed,
                                          a=self.drag,
                                          maxVal=self.max_speed)
                p = scrollOffset(data.widget)
                new_p = p - data.speed
                setScrollOffset(data.widget, new_p)

                if scrollOffset(data.widget) == p:
                    # If this scroll resulted in no change on the widget
                    # we reached the end of the list and set the speed to
                    # zero.
                    data.speed = QtCore.QPoint(0, 0)

                if data.speed == QtCore.QPoint(0, 0):
                    data.state = FlickData.Steady

        if count == 0:
            self.ticker.stop()

        super(FlickCharm, self).timerEvent(event)


def scrollOffset(widget):
    x = widget.horizontalScrollBar().value()
    y = widget.verticalScrollBar().value()
    return QtCore.QPoint(x, y)


def setScrollOffset(widget, p):
    widget.horizontalScrollBar().setValue(p.x())
    widget.verticalScrollBar().setValue(p.y())


def deaccelerate(speed, a=1, maxVal=64):

    x = max(min(speed.x(), maxVal), -maxVal)
    y = max(min(speed.y(), maxVal), -maxVal)
    if x > 0:
        x = max(0, x - a)
    elif x < 0:
        x = min(0, x + a)
    if y > 0:
        y = max(0, y - a)
    elif y < 0:
        y = min(0, y + a)
    return QtCore.QPoint(x, y)


def removeAll(list, val):
    found = False
    ret = []
    for element in list:
        if element == val:
            found = True
        else:
            ret.append(element)
    return found, ret
