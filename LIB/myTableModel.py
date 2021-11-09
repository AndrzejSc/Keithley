import PyQt5
from PyQt5 import QtGui
from PyQt5.QtCore import QAbstractTableModel
from PyQt5.QtCore import QObject, Qt


class MyTableModel(QAbstractTableModel, QObject):
    def __init__(self, data):
        super(MyTableModel, self).__init__()
        self._data = data

    def setNewData(self, newData):
        # print(newData)
        self._data = newData

    def data(self, index, role=None):
        if role == Qt.DisplayRole:
            value = self._data.iloc[index.row(), index.column()]
            return str(value)

        if role == Qt.ForegroundRole:
            value = self._data.iloc[index.row(), index.column()]
            if (isinstance(value, float)):
                # print (value)
                # print(self._data.iloc[index.row(), 5:14])
                if (value == min(self._data.iloc[index.row(), 4:14])):
                    return QtGui.QColor('blue')
                if (value == max(self._data.iloc[index.row(), 4:14])):
                    return QtGui.QColor('red')

        if role == Qt.BackgroundRole:
            value = self._data.iloc[index.row(), index.column()]

            if value == self._data.iloc[index.row(), 14]:
                if value < float(self._data.iloc[index.row(), 15]):
                    return QtGui.QColor('#AAFF7F')  # ('rgb(170, 255, 127)')
                else:
                    return QtGui.QColor('#FFAA7F')  # ('rgb(255,170,127)')

        if role == Qt.TextAlignmentRole:
            value = self._data.iloc[index.row(), index.column()]
            return Qt.AlignVCenter + Qt.AlignHCenter

    # def setData(self, index, newData, role=None):
    #     self._data = newData
    #     print(newData)
    #     if role == Qt.DisplayRole:
    #         value = self._data.iloc[index.row(), index.column()]
    #         return str(value)

    def rowCount(self, index=None):
        return self._data.shape[0]

    def columnCount(self, index=None):
        return self._data.shape[1]

    #def headerData(self, section: int, orientation: PySide2.QtCore.Qt.Orientation, role=None):
    def headerData(self, section: int, orientation: PyQt5.QtCore.Qt.Orientation, role=None):
        if role == Qt.DisplayRole:
            if orientation == Qt.Horizontal:
                return str(self._data.columns[section])
            if orientation == Qt.Vertical:
                return str(self._data.index[section])
