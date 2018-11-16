from app.vendor.Qt import QtGui
from app.vendor.Qt import QtWidgets
import credentials

app = QApplication([])
app.setQuitOnLastWindowClosed(False)

# Create the icon
avalon_core_icon = r'C:\Users\jakub.trllo\CODE\pype-setup\repos\avalon-launcher\launcher\res\icon\main.png'
icon = QIcon(avalon_core_icon)

clipboard = QApplication.clipboard()
dialog = QColorDialog()

def logout():
    credentials.

def copy_color_hsv():
    if dialog.exec_():
        color = dialog.currentColor()
        clipboard.setText("hsv(%d, %d, %d)" % (
            color.hue(), color.saturation(), color.value()
        ))
def exit():
    self.close()
# Create the tray
tray = QSystemTrayIcon()
tray.setIcon(icon)
tray.setVisible(True)

# Create the menu
menu = QMenu()
exit = QAction("Exit")
exit.triggered.connect(exit)

logout = QAction("Logout")
logout.triggered.connect(logout)

action3 = QAction("HSV")
action3.triggered.connect(copy_color_hsv)

menu.addAction(exit)
# menu.addAction(action2)
# menu.addAction(action3)

# Add the menu to the tray
tray.setContextMenu(menu)

app.exec_()
