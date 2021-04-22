import os
import sys
paths = [
    r"C:\Users\iLLiCiT\PycharmProjects\pype3\.venv\Lib\site-packages",
    r"C:\Users\iLLiCiT\PycharmProjects\pype3",
    r"C:\Users\iLLiCiT\PycharmProjects\pype3\repos\avalon-core"
]
for path in paths:
    sys.path.append(path)

os.environ["OPENPYPE_DATABASE_NAME"] = "openpype"
os.environ["OPENPYPE_MONGO"] = "mongodb://localhost:2707"
os.environ["AVALON_TIMEOUT"] = "1000"

from project_manager import Window

from Qt import QtWidgets


def main():
    app = QtWidgets.QApplication([])

    window = Window()
    window.show()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
