# -*- coding: utf-8 -*-
import os

from PySide2 import QtWidgets, QtGui, QtCore


class ShowFolderTreeThread(QtCore.QThread):

    def __init__(self, p, treeWidget: QtWidgets.QTreeWidget, root_dir: str = "."):
        super().__init__(p)
        self.root_dir = root_dir
        self.treeWidget = treeWidget

    def list_folder(self, parent_path: str, parent_item=None, max_depth: int = 3):
        if max_depth <= 0:
            return
        try:
            for content in os.listdir(parent_path):
                absolute_path = os.path.join(parent_path, content)
                is_dir: bool = os.path.isdir(absolute_path)
                item = QtWidgets.QTreeWidgetItem(parent_item or self.treeWidget)
                item.setText(0, content)
                item.setText(1, "Folder" if is_dir else os.path.splitext(content)[1])
                if is_dir:
                    self.list_folder(absolute_path, item, max_depth - 1)
        except:
            pass

    def run(self):
        try:
            self.treeWidget.clear()
            self.list_folder(self.root_dir)
        except Exception as e:
            print(type(e), e)


class MainWindow(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.treeWidget = QtWidgets.QTreeWidget(self)
        self.treeWidget.setHeaderLabel("name")
        self.pushButton = QtWidgets.QPushButton(self)
        self.pushButton.setObjectName("pushButton")
        self.pushButton.setText("Refresh")
        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(self.treeWidget)
        layout.addWidget(self.pushButton)
        self.setLayout(layout)
        self.resize(400, 600)
        self.workThread = ShowFolderTreeThread(self, self.treeWidget)
        self.workThread.setObjectName("workThread")

        self.workThread.finished.connect(self.thread_finished)
        self.pushButton.clicked.connect(self.start_thread)

    def start_thread(self):
        self.pushButton.setDisabled(True)  # fixme: cause Python not responding if set btn to disabled and then enabled
        self.workThread.start()

    def thread_finished(self):
        self.pushButton.setEnabled(True)  # fixme: cause Python not responding if set btn to disabled and then enabled
        print("thread_finished")


if __name__ == '__main__':
    import sys

    try:
        app = QtWidgets.QApplication(sys.argv)
        w = MainWindow()
        w.show()
        sys.exit(app.exec_())
    except Exception as e:
        print(type(e), e)
        raise e